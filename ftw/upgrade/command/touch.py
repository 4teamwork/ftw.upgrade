from datetime import datetime
from datetime import timedelta
from ftw.upgrade.directory.scaffold import DATETIME_FORMAT
from ftw.upgrade.directory.scanner import UPGRADESTEP_DATETIME_REGEX
from path import Path
import argparse
import re
import sys


NAME_RE = re.compile(r'^.*/?\d{14}_([^/]*)$')
TIMESTAMP_RE = re.compile(r'^.*/?(\d{14})_[^/]*$')


def setup_argparser(commands):
    command = commands.add_parser(
        'touch',
        help='Update the timestamp of an existing upgrade step.',
        description=touch_command.__doc__)
    command.set_defaults(func=touch_command)

    command.add_argument('path',
                         help='Path to the upgrade step directory to touch.',
                         type=upgrade_step_path)

    order = command.add_mutually_exclusive_group()
    order.add_argument('--after', '-a',
                       metavar='path',
                       dest='after_path',
                       help='Move after this upgrade step directory.',
                       type=upgrade_step_path)

    order.add_argument('--before', '-b',
                       metavar='path',
                       dest='before_path',
                       help='Move before this upgrade step directory.',
                       type=upgrade_step_path)


def touch_command(args):
    """Updates the timestamp of an existing upgrade step.
    This is useful for changing the order of upgrade steps.
    """

    parents = set(map(Path.dirname,
                      filter(bool, (args.path,
                                    args.after_path,
                                    args.before_path))))
    if len(parents) > 1:
        print >>sys.stderr, 'ERORR: All paths must be in the same directory,', \
            'got:'
        for parent in parents:
            print '-', parent
        sys.exit(1)

    new_date = find_new_date(args)
    new_name = NAME_RE.sub(
        r'{0}_\1'.format(new_date.strftime(DATETIME_FORMAT)),
        args.path.name)
    new_path = args.path.dirname().joinpath(new_name)
    args.path.rename(new_path)
    print 'New path:', new_path


def upgrade_step_path(path):
    path = Path(path).abspath()

    if not path.isdir():
        raise argparse.ArgumentTypeError(
            '"{0}" does not exist or is not a directory'.format(path))

    if not path_to_datetime(path):
        raise argparse.ArgumentTypeError(
            '"{0}" has not a valid upgrade step name or does'
            ' not contain an upgrade.py.'.format(path.name))

    return path


def find_new_date(args):
    before = path_to_datetime(args.before_path)
    after = path_to_datetime(args.after_path)
    if not before and not after:
        return datetime.now()

    upgrades = sorted(
        filter(None,
               map(path_to_datetime,
                   Path(args.path.dirname()).glob('*/upgrade.py'))))
    upgrades.remove(path_to_datetime(args.path))

    if after and upgrades[-1] == after:
        return after + timedelta(days=1)

    if before and upgrades[0] == before:
        return before - timedelta(days=1)

    if not before:
        before = upgrades[upgrades.index(after) + 1]

    if not after:
        after = upgrades[upgrades.index(before) - 1]

    return after + (before - after) / 2


def path_to_datetime(path):
    if path is None:
        return None

    if not path.name == 'upgrade.py':
        path = path.joinpath('upgrade.py')

    match = UPGRADESTEP_DATETIME_REGEX.match(path)
    if not match:
        return None

    return datetime.strptime(match.group(1), '%Y%m%d%H%M%S')
