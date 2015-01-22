from ftw.upgrade.command import create
from ftw.upgrade.command import list_profiles
from ftw.upgrade.command import list_proposed
from ftw.upgrade.command import sites
from ftw.upgrade.command import touch
from pkg_resources import get_distribution
import argcomplete
import argparse
import sys


class UpgradeCommand(object):

    def __init__(self):
        self.parser = argparse.ArgumentParser(
            sys.argv[0],
            description='ftw.upgrade command line tool.')

        version = get_distribution('ftw.upgrade').version
        self.parser.add_argument('--version', action='version',
                                 version='%(prog)s {0}'.format(version))

        argcomplete.autocomplete(self.parser)

        commands = self.parser.add_subparsers(help='Command')
        create.setup_argparser(commands)
        sites.setup_argparser(commands)
        touch.setup_argparser(commands)

        list_command = commands.add_parser(
            'list',
            help='List upgrades or profiles.')
        list_commands = list_command.add_subparsers()
        list_profiles.setup_argparser(list_commands)
        list_proposed.setup_argparser(list_commands)

    def __call__(self):
        args = self.parser.parse_args()
        args.func(args)


def main():
    UpgradeCommand()()
