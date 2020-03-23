from collections import defaultdict
from contextlib import contextmanager
from copy import deepcopy
from ftw.upgrade.exceptions import CyclicDependencies
from path import Path
from six.moves import map
from zope.component.hooks import getSite

import logging
import math
import os
import re
import stat
import tarjan.tc
import transaction


def topological_sort(items, partial_order):
    """Perform topological sort.
    items is a list of items to be sorted.
    partial_order is a list of pairs. If pair (a,b) is in it, it means
    that item a should appear before item b.
    Returns a list of the items in one of the possible orders, or None
    if partial_order contains a loop.
    Source: http://www.bitformation.com/art/python_toposort.html
    """

    def add_node(graph, node):
        """Add a node to the graph if not already exists."""
        if node not in graph:
            graph[node] = [0]  # 0 = number of arcs coming into this node.

    def add_arc(graph, fromnode, tonode):
        """Add an arc to a graph. Can create multiple arcs.
        The end nodes must already exist."""
        graph[fromnode].append(tonode)
        # Update the count of incoming arcs in tonode.
        graph[tonode][0] = graph[tonode][0] + 1

    # step 1 - create a directed graph with an arc a->b for each input
    # pair (a,b).
    # The graph is represented by a dictionary. The dictionary contains
    # a pair item:list for each node in the graph. /item/ is the value
    # of the node. /list/'s 1st item is the count of incoming arcs, and
    # the rest are the destinations of the outgoing arcs. For example:
    #           {'a':[0,'b','c'], 'b':[1], 'c':[1]}
    # represents the graph:   c <-- a --> b
    # The graph may contain loops and multiple arcs.
    # Note that our representation does not contain reference loops to
    # cause GC problems even when the represented graph contains loops,
    # because we keep the node names rather than references to the nodes.
    graph = {}
    for v in items:
        add_node(graph, v)
    for a, b in partial_order:
        add_arc(graph, a, b)

    # Step 2 - find all roots (nodes with zero incoming arcs).
    roots = [node for (node, nodeinfo) in graph.items() if nodeinfo[0] == 0]
    roots.sort()

    # step 3 - repeatedly emit a root and remove it from the graph. Removing
    # a node may convert some of the node's direct children into roots.
    # Whenever that happens, we append the new roots to the list of
    # current roots.
    sorted_ = []
    while len(roots) != 0:
        # If len(roots) is always 1 when we get here, it means that
        # the input describes a complete ordering and there is only
        # one possible output.
        # When len(roots) > 1, we can choose any root to send to the
        # output; this freedom represents the multiple complete orderings
        # that satisfy the input restrictions. We arbitrarily take one of
        # the roots using pop(). Note that for the algorithm to be efficient,
        # this operation must be done in O(1) time.
        root = roots.pop()
        sorted_.append(root)
        for child in graph[root][1:]:
            graph[child][0] = graph[child][0] - 1
            if graph[child][0] == 0:
                roots.append(child)
        del graph[root]
    if len(graph.items()) != 0:
        # There is a loop in the input.
        return None
    return sorted_


def find_cyclic_dependencies(dependencies):
    deps = defaultdict(list)
    for first, second in dependencies:
        deps[first].append(second)

    cyclic_dependencies = []
    for name, closure in tarjan.tc.tc(deps).items():
        if name in closure and closure not in cyclic_dependencies:
            cyclic_dependencies.append(closure)

    return cyclic_dependencies


class SizedGenerator(object):

    def __init__(self, generator, length):
        self._length = length
        self._generator = generator

    def __iter__(self):
        return self._generator.__iter__()

    def __len__(self):
        return self._length


class SavepointIterator(object):
    """An iterator that creates a savepoint every n items.

    The goal of this iterator is to move data from the current transaction to
    the disk in order to free up RAM.
    """

    def __init__(self, iterable, threshold, logger=None):
        self.iterable = iterable
        self.threshold = threshold
        self.logger = logger

        if self.logger is None:
            self.logger = logging.getLogger('ftw.upgrade')

        if not threshold:
            raise ValueError("Threshold must be a non-zero value")

    def __iter__(self):
        for i, item in enumerate(self.iterable):
            if i % self.threshold == 0:
                optimize_memory_usage()
                self.logger.info("Created savepoint at %s items" % i)
            yield item

    def __len__(self):
        return self.iterable.__len__()

    @classmethod
    def build(cls, iterable, threshold=None, logger=None):
        if threshold is None:
            threshold = cls.get_default_threshold()

        if threshold:
            return SavepointIterator(iterable, threshold, logger)
        else:
            return iterable

    @staticmethod
    def get_default_threshold():
        """Returns the default savepoint threshold.

        The savepoint iterator threshold can be configured with an environment
        variable ``UPGRADE_SAVEPOINT_THRESHOLD``.
        When set to ``"None"``, savepoints are disabled.
        """
        value = os.environ.get('UPGRADE_SAVEPOINT_THRESHOLD', None)
        if value is None:
            # default unchanged; use application default
            return 1000

        value = value.strip().lower()
        if value == 'none':
            # threshold disabled
            return None

        try:
            value = int(value)
        except ValueError:
            raise ValueError('Invalid savepoint threshold {!r}'.format(value))

        if value > 0:
            return value
        else:
            raise ValueError('Invalid savepoint threshold {!r}'.format(value))


def optimize_memory_usage():
    """Optimizes the current memory usage by garbage collecting objects.

    The function creates a transaction savepoint in order to move pending
    changes from the memory to the disk.
    Afterwards the ZODB connection's pickle cache is notified to garbage
    collect objects, when necessary, so that the configured ZODB cache sizes
    are respected.

    The tradeoff of this function is a low memory footprint versus a speed:
    objects may be removed which will later be used again and have to be loaded
    again from the ZODB.
    """
    transaction.savepoint(optimistic=True)
    # By calling `cacheGC` on the connection, the pickle cache gets a
    # chance to respect the configured zodb cache size by garbage
    # collecting "older" objects (LRU).
    # This only works well when we've created a savepoint in advance,
    # which moves the changes to the disk.
    getSite()._p_jar.cacheGC()


def get_sorted_profile_ids(portal_setup):
    """Returns a sorted list of profile ids (without profile- prefix).
    The sorting is done by resolving the dependencies and performing
    a topological graph sort.
    If there are circular dependencies a CyclicDependencies exception
    is thrown.
    """
    profile_ids = []
    dependencies = []

    for profile in portal_setup.listProfileInfo():
        profile_ids.append(profile['id'])

    for profile in portal_setup.listProfileInfo():
        for dependency in (list(profile.get('dependencies') or []) +
                           list(profile.get('ftw.upgrade:dependencies') or [])):
            dependency = re.sub('^profile-', '', dependency)
            if dependency in profile_ids:
                dependencies.append((profile['id'], dependency))

    order = topological_sort(profile_ids, dependencies)

    if order is None:
        raise CyclicDependencies(
            dependencies,
            find_cyclic_dependencies(deepcopy(dependencies)))
    else:
        return list(reversed(order))


def format_duration(seconds):
    """Makes a duration in seconds human readable.
    Supports hours, minutes and seconds.
    """

    seconds = math.ceil(seconds)
    hours, remainder = divmod(seconds, 60 * 60)
    minutes, seconds = divmod(remainder, 60)

    result = []

    if hours == 1:
        result.append('1 hour')
    elif hours > 1:
        result.append('%i hours' % hours)

    if minutes == 1:
        result.append('1 minute')
    elif minutes > 1:
        result.append('%i minutes' % minutes)

    if seconds == 1:
        result.append('1 second')
    elif seconds > 1:
        result.append('%i seconds' % seconds)

    if len(result) == 0:
        return '0 seconds'
    else:
        return ', '.join(result)


def subject_from_docstring(docstring):
    """Extracts and returns the subject of a docstring.
    The subject consists of all lines from the beginning to the
    first empty line. Newlines are stripped.
    """
    lines = list(map(str.strip, docstring.strip().splitlines()))
    try:
        lines.index('')
    except ValueError:
        pass  # '' is not in list
    else:
        lines = lines[:lines.index('')]

    return ' '.join(lines).strip()


def get_tempfile_authentication_directory(directory=None):
    """Finds the buildout directory and returns the absolute path to the
    relative directory var/ftw.upgrade-authentication/.
    If the directory does not exist it is created.
    """
    directory = Path(directory) or Path.getcwd()
    if not directory.joinpath('bin', 'buildout').isfile():
        return get_tempfile_authentication_directory(directory.parent)

    auth_directory = directory.joinpath('var', 'ftw.upgrade-authentication')
    if not auth_directory.isdir():
        auth_directory.mkdir(mode=0o770)

    # Verify that "others" do not have any permissions on this directory.
    if auth_directory.stat().st_mode & stat.S_IRWXO:
        raise ValueError('{0} has invalid mode: "others" should not have '
                         'any permissions'.format(auth_directory))

    return auth_directory


class StartsWithLogFilter(logging.Filter):
    """Filter messages that start with criteria."""

    def __init__(self, criteria):
        self.criteria = criteria

    def filter(self, record):
        return not record.getMessage().startswith(self.criteria)


@contextmanager
def log_silencer(logger_name, criteria):
    """Prevents messages that start with `criteria` from being logged to the
    logger that is registered as `logger_name`.
    """
    log = logging.getLogger(logger_name)
    filt = StartsWithLogFilter(criteria)
    log.addFilter(filt)

    try:
        yield
    finally:
        log.removeFilter(filt)


def get_portal_migration(context):
    """Always use a portal_migration tool wrapped in a RequestContainer.

    The portal_migration tool is registered as a tool utility by Plone. This
    implies that it can work when fetched "out of thin air" as a utility.
    However, this is not strictly the case: Some Plone upgrades make use of
    self.REQUEST (directly or indirectly), which only works if the
    portal_migration tool is wrapped in a RequestContainer.

    If portal_migration is fetched via getToolByName, it *won't* be wrapped in
    a RequestContainer, because getToolByName first looks for a utility,
    and if it finds one, happily returns that.

    Instead, the portal_migration tool needs to be looked up via acquisition
    (using getattr). This is what Plone itself does in its @@plone-upgrade
    view, and it will lead to the portal_migration tool having a
    RequestContainer in its AQ chain.

    Please see 4teamwork/ftw.upgrade#170 for a more in depth explanation.
    """
    portal_migration = getattr(context, 'portal_migration')
    return portal_migration
