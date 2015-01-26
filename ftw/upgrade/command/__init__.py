from ftw.upgrade.command import create
from ftw.upgrade.command import help
from ftw.upgrade.command import install
from ftw.upgrade.command import list_cmd
from ftw.upgrade.command import sites
from ftw.upgrade.command import touch
from ftw.upgrade.command.formatter import FlexiFormatter
from ftw.upgrade.command.terminal import TERMINAL
from pkg_resources import get_distribution
import argcomplete
import argparse
import sys


VERSION = get_distribution('ftw.upgrade').version


DOCS = """
{t.bold}DESCRIPTION:{t.normal}
    The bin/upgrade script helps to create upgrade steps as well as to \
inspect the upgrades of a Plone site and install upgrades. \
The command is installed by the "ftw.upgrade" Plone addon package.

{t.bold}CREATING AND MANAGING UPGRADES:{t.normal}
    For using the "create" and "touch" command to manage upgrade steps on the \
file system, the package under development must use the \
"upgrade-step:directory" ZCML directive to declare an upgrade step directory, \
which should be named "upgrades".

    The "create" command then allows to easily generate upgrades with the \
current timestamp as destination version, the "touch" command on the other \
hand allows to change the order of upgrades by updating the timestamp \
(destination version).

{t.bold}LISTING AND INSTALLING UPGRADES:{t.normal}
    In order to use the commands "sites", "list" and "install" a Zope \
instance must be running, where "ftw.upgrade" is available and the \
"upgrades-api" endpoint is available.

{t.bold}ZOPE INSTANCE DISCOVERY:{t.normal}
    The Zope instance is discovered automatically by searching for all \
"zope.conf" files in "parts/instance*" of the buildout directory, looking up \
the instance port and testing whether the port is bound on localhost. If multiple \
instances are running, the first one running is used.

{t.bold}AUTHENTICATION:{t.normal}
    The JSON API requires authentication as a "Manager" user by using basic \
authentication. The authentication credentials can be passed with the \
"--auth" argument in form "<username>:<password>" for all commands requiring \
authentication.

    Alternatively, the credentials can be set in the "UPGRADE_AUTHENTICATION" \
environment variable which will be used as default for the "--auth" argument.

{t.bold}VIRTUAL HOSTING:{t.normal}
    For some upgrade steps it is important that "absolute_url()" returns a \
public URL, for example when contacting external services. \
By setting the environment variable "UPGRADE_PUBLIC_URL", "bin/upgrade" \
automatically configures the virtual host monster. \
Be aware that the Plone site URL part will not be part of the public URL. \
This means the public URL must point to the Plone site which is selected \
with the "--site" argument.

    Examples:
[quote]
$ UPGRADE_PUBLIC_URL="https://my.site.com/" bin/upgrade
$ UPGRADE_PUBLIC_URL="http://my.site.com/foo/bar" bin/upgrade
[/quote]

{t.bold}MORE INFORMATION:{t.normal}
    Project Homepage: https://github.com/4teamwork/ftw.upgrade
    ftw.upgrade version: {version}
""".format(t=TERMINAL, version=VERSION).strip()


class UpgradeArgumentParser(argparse.ArgumentParser):
    def __init__(self, *args, **kwargs):
        kwargs['formatter_class'] = FlexiFormatter
        super(UpgradeArgumentParser, self).__init__(*args, **kwargs)


class UpgradeCommand(object):

    def __init__(self):
        self.parser = UpgradeArgumentParser(
            sys.argv[0],
            epilog=DOCS)

        self.parser.add_argument('--version', action='version',
                                 version='%(prog)s {0}'.format(VERSION))

        argcomplete.autocomplete(self.parser)

        commands = self.parser.add_subparsers(help='Command')
        create.setup_argparser(commands)
        install.setup_argparser(commands)
        sites.setup_argparser(commands)
        touch.setup_argparser(commands)
        list_cmd.setup_argparser(commands)

        # Register as last.
        help.setup_argparser(commands)

    def __call__(self):
        args = self.parser.parse_args()
        setattr(args, 'parser', self.parser)
        args.func(args)


def main():
    UpgradeCommand()()
