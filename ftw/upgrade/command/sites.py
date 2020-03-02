from __future__ import print_function
from ftw.upgrade.command.jsonapi import add_json_argument
from ftw.upgrade.command.jsonapi import add_requestor_authentication_argument
from ftw.upgrade.command.jsonapi import error_handling
from ftw.upgrade.command.jsonapi import with_api_requestor
from ftw.upgrade.command.terminal import TERMINAL

import six


DOCS = """
{t.bold}DESCRIPTION:{t.normal}
    Discover Plone sites on this Zope instance and list them.

{t.bold}EXAMPLES:{t.normal}
[quote]
    $ bin/upgrade sites
    $ bin/upgrade sites --auth admin:admin
    $ bin/upgrade sites --auth admin:admin --json
[/quote]
""".format(t=TERMINAL).strip()


def setup_argparser(commands):
    command = commands.add_parser(
        'sites',
        help='Discover Plone sites.',
        description=DOCS)
    command.set_defaults(func=sites_command)
    add_requestor_authentication_argument(command)
    add_json_argument(command)


@with_api_requestor
@error_handling
def sites_command(args, requestor):
    response = requestor.GET('list_plone_sites')

    if args.json:
        print(response.text)
    else:
        for site in response.json():
            print(site['path'].ljust(20), six.ensure_str(site['title']))
