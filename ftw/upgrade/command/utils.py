from __future__ import print_function
from path import Path
from six import StringIO

import contextlib
import os
import sys


def find_egginfo(path=None):
    path = path or Path(os.getcwd())
    if not path or path == '/':
        print('WARNING: no *.egg-info directory could be found.',
              file=sys.stderr)
        return None

    egginfos = path.dirs('*.egg-info')
    if len(egginfos) == 0:
        return find_egginfo(path.dirname())

    if len(egginfos) > 1:
        print('WARNING: more than one *.egg-info directory found.',
              file=sys.stderr)
        return None

    return egginfos[0]


def find_package_namespace_path(egginfo):
    with egginfo.joinpath('top_level.txt').open() as top_level_file:
        top_level_path = top_level_file.read().strip()

    return egginfo.dirname().joinpath(top_level_path)


@contextlib.contextmanager
def capture():
    oldout = sys.stdout
    try:
        sys.stdout = StringIO()
        yield sys.stdout
    finally:
        sys.stdout = oldout
