from ftw.upgrade.exceptions import CyclicDependencies
import itertools
import json
import math
import os


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


class SizedGenerator(object):

    def __init__(self, generator, length):
        self._length = length
        self._generator = generator

    def __iter__(self):
        return self._generator.__iter__()

    def __len__(self):
        return self._length


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
        raise CyclicDependencies(dependencies)
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


def pretty_json(fn):
    """Decorator to encode a method's result in JSON and pretty print it.
    """
    def wrapper(self):
        return json.dumps(fn(self),
                          sort_keys=True,
                          indent=4,
                          separators=(',', ': '))

    # set docstring for wrapped method, otherwise it won't get published
    wrapper.__doc__ = fn.__doc__
    return wrapper


def join_lines(fn):
    """Decorator that joins a sequence of lines with newlines.
    """
    def wrapped(self, *args, **kwargs):
        return '\n'.join(fn(self, *args, **kwargs))
    return wrapped


def distribute_across_columns(items, num_cols):
    """Distribute items evenly across columns.
    """
    cols = [[] for _n in range(num_cols)]
    cycle = itertools.cycle(range(num_cols))

    for item in items:
        col_idx = cycle.next()
        cols[col_idx].append(item)
    return cols


def list_buildouts(cluster_dir):
    """Lists all directories in `cluster_dir` that look like a bootstrapped
    buildout.
    """
    buildouts = []

    for buildout in os.listdir(cluster_dir):
        buildout_path = os.path.join(cluster_dir, buildout)
        bin_buildout_path = os.path.join(buildout_path, 'bin/buildout')
        if os.path.isdir(buildout_path) and os.path.exists(bin_buildout_path):
            buildouts.append(buildout)
    return buildouts


def py_interpreter_from_shebang(path):
    """Extracts the Python interpreter path from the shebang of a given script.
    """
    f = open(path, 'r')
    shebang = f.readline()
    if not shebang.startswith('#!'):
        raise AssertionError("Given script %s doesn't contain a shebang on "
                             "the first line.")
    py_path = shebang.replace('#!', '').split(' ')[0]
    return os.path.abspath(py_path)
