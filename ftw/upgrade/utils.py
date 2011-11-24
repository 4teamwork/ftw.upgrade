import os
import sys


def get_dotted_name(cls):
    """Returns the dotted name of a class.

    Arguments:
    `cls` -- The class.
    """
    return '.'.join((cls.__module__, cls.__name__))


def get_modules(dottedname):
    package = get_module(dottedname)

    packagename, ext_ = os.path.splitext(os.path.basename(package.__file__))
    if packagename != '__init__':
        return [package]

    path = os.path.abspath(os.path.dirname(package.__file__))

    modules = []

    for dirpath, dirnames, filenames in os.walk(path):
        for filename in filenames:
            basename, ext_ = os.path.splitext(filename)
            if ext_ not in ('.py', '.pyc', 'pyo'):
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
    path = os.path.normpath(path)
    basepath = os.path.normpath(basepath)

    if not path.startswith(basepath):
        raise ValueError(
            '`path` (%s) does not begin with `basepath` (%s)'% (
                path, basepath))

    end = path[len(basepath) + 1:]

    basename, ext_ = os.path.splitext(os.path.basename(end))
    if basename == '__init__':
        end = os.path.dirname(end)
    else:
        end = os.path.dirname(end) + os.sep + basename

    if len(end) == 0:
        return prefix

    dottedname = end.replace(os.sep, '.')
    if prefix:
        return '.'.join((prefix, dottedname))
    else:
        return dottedname


def get_module(dottedname):
    __import__(dottedname)
    return sys.modules[dottedname]

