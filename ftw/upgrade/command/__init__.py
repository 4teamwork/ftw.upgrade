from ftw.upgrade.command import combine_bundles
from ftw.upgrade.command import create
from ftw.upgrade.command import help
from ftw.upgrade.command import install
from ftw.upgrade.command import list_cmd
from ftw.upgrade.command import plone_upgrade
from ftw.upgrade.command import plone_upgrade_needed
from ftw.upgrade.command import recook
from ftw.upgrade.command import sites
from ftw.upgrade.command import touch
from ftw.upgrade.command import user
from ftw.upgrade.command.formatter import FlexiFormatter
from ftw.upgrade.command.terminal import TERMINAL
from ftw.upgrade.command.utils import capture
from pkg_resources import get_distribution

import argcomplete
import argparse
import json
import logging
import sys


VERSION = get_distribution('ftw.upgrade').version
logger = logging.getLogger('ftw.upgrade')


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
"parts/*/etc/zope.conf" files in the buildout directory, looking up \
the instance port and testing whether the port is bound on localhost.
If multiple instances are running, the first one running is used.

{t.bold}AUTHENTICATION:{t.normal}
    There are three authentication options which are tested and used in this \
order:

    - "--auth" argument for basic authentication
    - "UPGRADE_AUTHENTICATION" environment variable for basic authentication
    - automatic tempfile based authorization negotiation, using the \
      automatically generated manager user "system-upgrade".

    {t.bold}"--auth" argument authentication{t.normal}
    Commands requiring authentication have a "--auth" argument which precede \
the tempfile negotiation mechanism. \
It uses basic authentication. \
The value is expected to be "<username>:<password>". \
The user should have the "Manager" role.

    {t.bold}"UPGRADE_AUTHENTICATION" environment variable{t.normal}
    When no "--auth" argument is used, the "UPGRADE_AUTHENTICATION" \
environment variable is tested for authentication information. \
This works exactly like the "--auth" argument.

    {t.bold}Tempfile negotiation authentication{t.normal}
    The automatic tempfile negotiation is used when neither the "--auth" \
argument nor the "UPGRADE_AUTHENTICATION" environment variable is used. \
It creates a tempfile, readable only for the owner user and writes a random \
hash to the file. The filename and the hash is submitted as request header \
and the backend reads the tempfile and verifies the content.
    The idea is that if a user has access to the machine with the user \
running Zope, he can easily create an emergency administator user from the \
command line and acquire full manager access to the Zope installation. \
By being able to write the tempfile as this user on the server machine \
the access is verified.
    When using this mechanism, a manager user is created at Zope app level, \
named "system-upgrade". The user has a random password. All requests are \
then authenticated with this user.
    The temporary file is written to \
[buildout-directory]var/ftw.upgrade-authentication

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
        combine_bundles.setup_argparser(commands)
        create.setup_argparser(commands)
        install.setup_argparser(commands)
        list_cmd.setup_argparser(commands)
        plone_upgrade.setup_argparser(commands)
        plone_upgrade_needed.setup_argparser(commands)
        recook.setup_argparser(commands)
        sites.setup_argparser(commands)
        touch.setup_argparser(commands)
        user.setup_argparser(commands)

        # Register as last.
        help.setup_argparser(commands)

    def __call__(self):
        args = self.parser.parse_args()
        configure_logging(args)
        setattr(args, 'parser', self.parser)
        if getattr(args, 'all_sites', False):
            info = {}
            while True:
                try:
                    with capture() as out:
                        args.func(args)
                    output = out.getvalue().strip()
                    if getattr(args, 'json', False):
                        # "[]" must be turned into [] and put in dictionary.
                        output = json.loads(output)
                        info[args.picked_site] = output
                    else:
                        logger.info('Acting on site {0}'.format(
                            args.picked_site))
                        print(output)
                except StopIteration:
                    break
            if getattr(args, 'json', False):
                # Pretty print the output of all sites.
                print((json.dumps(info, indent=4)))
        else:
            args.func(args)


def configure_logging(args):
    # Extend the level names with colors.
    logging.addLevelName(
        logging.INFO, '{t.green}{levelname}{t.normal}'.format(
            t=TERMINAL, levelname=logging.getLevelName(logging.INFO)))
    for level in (logging.WARN, logging.ERROR, logging.CRITICAL):
        logging.addLevelName(
            level, '{t.red_bold}{levelname}{t.normal}'.format(
                t=TERMINAL, levelname=logging.getLevelName(level)))
    if getattr(args, 'verbose', False):
        # Log debug level and higher for all loggers.
        start_level = logging.DEBUG
        format = '%(levelname)s %(name)s: %(message)s'
        logging.basicConfig(level=start_level, format=format)
    else:
        # Log info level and higher, only for our own logger.
        start_level = logging.INFO
        format = '%(levelname)s: %(message)s'
        logging.basicConfig(level=start_level, format=format)
        for handler in logging.root.handlers:
            handler.addFilter(logging.Filter('ftw.upgrade'))


def main():
    UpgradeCommand()()
