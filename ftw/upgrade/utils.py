from ftw.upgrade.interfaces import IUpgrade
from ftw.upgrade.upgrade import BaseUpgrade
import inspect
import os
import sys


def get_dotted_name(cls):
    """Returns the dotted name of a class.

    Arguments:
    `cls` -- The class.
    """
    return '.'.join((cls.__module__, cls.__name__))


def get_modules(package):

    packagename, _ = os.path.splitext(os.path.basename(package.__file__))
    if packagename != '__init__':
        return [package]

    path = os.path.abspath(os.path.dirname(package.__file__))

    modules = []

    for dirpath, _, filenames in os.walk(path):
        for filename in filenames:
            _, ext = os.path.splitext(filename)
            if ext not in ('.py', '.pyc', 'pyo'):
                continue

            filepath = os.path.join(dirpath, filename)
            dottedname = filepath_to_dottedname(path, filepath,
                                                prefix=package.__name__)
            module = get_module(dottedname)

            if module not in modules:
                modules.append(module)

    return modules


def filepath_to_dottedname(basepath, path, prefix=''):
    """Converts a filename `path` to a dotted name by removing the `basepath`
    and converting the rest.
    """

    fullpath = os.path.normpath(path)
    basepath = os.path.normpath(basepath)

    if not fullpath.startswith(basepath):
        raise ValueError(
            '`path` (%s) does not begin with `basepath` (%s)' % (
                path, basepath))

    path = fullpath[len(basepath) + 1:]

    directory, filename = os.path.split(path)
    basename, _ = os.path.splitext(filename)

    if basename == '__init__' and not directory:
        return prefix

    elif basename == '__init__':
        dottedname = os.path.join(prefix, directory)

    else:
        dottedname = os.path.join(prefix, directory, basename)

    return dottedname.replace(os.sep, '.')


def get_module(dottedname):
    __import__(dottedname)
    return sys.modules[dottedname]


def order_upgrades(upgrades):
    """Orders a list of UpgradeInfo objects (`upgrades`) by dependencies.
    """
    # XXX: this function can not handle circular dependencies.
    upgrades_dict = {}
    ordered_dottednames = []

    for upgrade in upgrades:
        upgrades_dict[upgrade.get_title()] = upgrade

    for upgrade in upgrades:
        if not upgrade.is_installed() and upgrade not in ordered_dottednames:
            branch = get_dependency_branch([upgrade])
            for item in branch:
                if item not in ordered_dottednames:
                    ordered_dottednames.append(item)

    return ordered_dottednames


def get_dependency_branch(items):
    branch = []
    for item in items:
        dependencies = item.get_dependencies()
        if len(dependencies) != 0:
            branch.extend(get_dependency_branch(dependencies))
        branch.append(item)
    return branch


def get_classes_from_module(module, implements=None):
    """Returns all classes defined or imported in a ``module``.
    If ``implements`` is an interface the classes are filtered and only those
    implementing the ``implements`` interface are yielded.
    """

    for _, obj in inspect.getmembers(module):
        if not inspect.isclass(obj):
            continue

        if implements and not implements.implementedBy(obj):
            continue

        yield obj


def discover_upgrades(package):
    """Discover all classes within modules of a ``package``.
    """

    for module in get_modules(package):
        for cls in get_classes_from_module(module, implements=IUpgrade):
            if BaseUpgrade.__call__ == cls.__call__:
                continue
            yield cls
