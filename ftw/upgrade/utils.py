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
            '`path` (%s) does not begin with `basepath` (%s)'% (
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
    """Requires a Dict of UpgradeInfo objects.
       Since we get the dottedname as dependency it's alot easier to access the depended upgrade
    """
    ordered_upgrades=[]
    for k, v in upgrades.items():
        dependencies = v.get_dependencies()
