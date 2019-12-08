from __future__ import print_function
from ftw.upgrade.command.terminal import TERMINAL
from ftw.upgrade.command.utils import find_egginfo
from ftw.upgrade.command.utils import find_package_namespace_path
from ftw.upgrade.directory.scaffold import UpgradeStepCreator
from path import Path

import argparse
import sys


DOCS = """
{t.bold}DESCRIPTION:{t.normal}
    The "create" command creates a new upgrade step in the "upgrades" \
directory of this package.

    The created upgrade step works only when the "upgrades" directory is \
registered using the "{t.bold_green}upgrade-step:directory{t.normal}" \
directive in ZCML.

    The command creates a new directory within the "upgrades" directory and \
adds an "upgrade.py" file with a default upgrade step. \
The "title" argument is used for naming the directory as well as the \
upgrade step class in the generated "upgrade.py" file.

{t.bold}EXAMPLES:{t.normal}
[quote]
$ bin/upgrade create AddIndexesToCatalog
$ bin/upgrade create AddIndexesToCatalog --path src/my/package/upgrades
[/quote]
""".format(t=TERMINAL).strip()


def setup_argparser(commands):
    command = commands.add_parser('create',
                                  help='Create a new upgrade step.',
                                  description=DOCS)
    command.set_defaults(func=create_command)

    command.add_argument('--path', '-p',
                         metavar='upgrades-directory',
                         dest='upgrades_directory',
                         help='Path to the upgrades directory.'
                         ' The default path is searched by resolving the top'
                         ' level in the egg-info and looking for an "upgrades"'
                         ' directory.'
                         ' If no egg-info is found or there is no or multiple'
                         ' "upgrades" directories, the user has to provide the'
                         ' path explicitly.',
                         default=None,
                         type=upgrades_path)

    command.add_argument('title',
                         help='Title of the upgrade step.'
                         ' Either in camel case or with underscores.')


def create_command(args):
    upgrades_directory = args.upgrades_directory
    if upgrades_directory is None:
        upgrades_directory = default_upgrades_directory()

    if upgrades_directory is None:
        print('ERROR: Please provide the path to '
              'the upgrades directory with --path.', file=sys.stderr)
        sys.exit(1)

    creator = UpgradeStepCreator(upgrades_directory)
    upgrade_step_directory = creator.create(args.title)
    print('Created upgrade step at:', upgrade_step_directory)


def upgrades_path(path):
    path = Path(path).abspath()

    if not path.isdir():
        raise argparse.ArgumentTypeError(
            '"{0}" does not exist or is not a directory'.format(path))

    return path


def default_upgrades_directory():
    egginfo = find_egginfo()
    if not egginfo:
        return None

    package_namespace_path = find_package_namespace_path(egginfo)
    upgrades_dirs = tuple(package_namespace_path.walkdirs('upgrades'))
    if len(upgrades_dirs) == 0:
        print('WARNING: no "upgrades" directory could be found.', file=sys.stderr)
        return None

    if len(upgrades_dirs) > 1:
        print('WARNING: more than one "upgrades" directory found.', file=sys.stderr)
        return None

    return upgrades_dirs[0]
