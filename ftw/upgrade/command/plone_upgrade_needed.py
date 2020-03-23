from ftw.upgrade.command.jsonapi import add_requestor_authentication_argument
from ftw.upgrade.command.jsonapi import add_site_path_argument
from ftw.upgrade.command.jsonapi import error_handling
from ftw.upgrade.command.jsonapi import with_api_requestor
from ftw.upgrade.command.terminal import TERMINAL

import sys


DOCS = """
{t.bold}DESCRIPTION:{t.normal}
    Tells whether the Plone-site needs to be upgraded.

{t.bold}EXAMPLES:{t.normal}
[quote]
$ bin/upgrade plone_upgrade_needed --site Plone
[/quote]

""".format(t=TERMINAL).strip()


def setup_argparser(commands):
    command = commands.add_parser(
        'plone_upgrade_needed',
        help='Should the Plone site be upgraded?',
        description=DOCS)
    command.set_defaults(func=plone_upgrade_command)
    add_requestor_authentication_argument(command)
    add_site_path_argument(command)


@with_api_requestor
@error_handling
def plone_upgrade_command(args, requestor):
    response = requestor.GET('plone_upgrade_needed')
    print(response.text)
    if response.text.strip() not in ('true', 'false'):
        sys.exit(3)
