from collections import defaultdict
from copy import deepcopy
from ftw.upgrade.exceptions import CyclicDependencies
from path import Path
import logging
import math
import os
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
                transaction.savepoint()
                self.logger.info("Created savepoint at %s items" % i)
            yield item

    def __len__(self):
        return self.iterable.__len__()

    @classmethod
    def build(cls, iterable, threshold=None, logger=None):
        if threshold:
            return SavepointIterator(iterable, threshold, logger)
        else:
            return iterable


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
        if not profile.get('dependencies'):
            continue

        for dependency in profile.get('dependencies'):
            if dependency.startswith('profile-'):
                dependency = dependency.split('profile-', 1)[1]
            else:
                continue

            if dependency not in profile_ids:
                continue
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
    lines = map(str.strip, docstring.strip().splitlines())
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
        auth_directory.mkdir(mode=0700)

    if stat.S_IMODE(auth_directory.stat().st_mode) != 0700:
        raise ValueError('{0} has invalid mode.'.format(auth_directory))
    if auth_directory.stat().st_uid != os.getuid():
        raise ValueError('{0} has an invalid owner.'.format(auth_directory))

    return auth_directory
