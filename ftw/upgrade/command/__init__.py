from ftw.upgrade.command import create
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

        commands = self.parser.add_subparsers(help='Command', dest='command')
        create.setup_argparser(commands)

    def __call__(self):
        args = self.parser.parse_args()
        args.func(args)


def main():
    UpgradeCommand()()
