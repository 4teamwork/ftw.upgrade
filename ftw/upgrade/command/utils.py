from path import Path
import os
import stat
import sys


def find_egginfo(path=None):
    path = path or Path(os.getcwd())
    if not path or path == '/':
        print >>sys.stderr, 'WARNING: no *.egg-info directory could be found.'
        return None

    egginfos = path.dirs('*.egg-info')
    if len(egginfos) == 0:
        return find_egginfo(path.dirname())

    if len(egginfos) > 1:
        print >>sys.stderr, 'WARNING: more than one *.egg-info' + \
            ' directory found.'
        return None

    return egginfos[0]


def find_package_namespace_path(egginfo):
    with egginfo.joinpath('top_level.txt').open() as top_level_file:
        top_level_path = top_level_file.read().strip()

    return egginfo.dirname().joinpath(top_level_path)


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
