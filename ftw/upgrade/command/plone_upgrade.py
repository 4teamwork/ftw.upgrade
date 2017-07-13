from contextlib import closing
from ftw.upgrade.command.jsonapi import add_requestor_authentication_argument
from ftw.upgrade.command.jsonapi import add_site_path_argument
from ftw.upgrade.command.jsonapi import error_handling
from ftw.upgrade.command.jsonapi import with_api_requestor
from ftw.upgrade.command.terminal import TERMINAL
import sys


DOCS = """
{t.bold}DESCRIPTION:{t.normal}
    Upgrade Plone Site. \
This is what you would manually do in the @@plone-upgrade view.

{t.bold}EXAMPLES:{t.normal}
[quote]
$ bin/upgrade plone_upgrade --site Plone
[/quote]

""".format(t=TERMINAL).strip()


def setup_argparser(commands):
    command = commands.add_parser(
        'plone_upgrade',
        help='Upgrade Plone Site.',
        description=DOCS)
    command.set_defaults(func=plone_upgrade_command)
    add_requestor_authentication_argument(command)
    add_site_path_argument(command)


# expected output
expected = (
    u'Plone Site was already up to date.',
    u'Plone Site has been updated.')


@with_api_requestor
@error_handling
def plone_upgrade_command(args, requestor):
    action = 'plone_upgrade'
    params = ()

    with closing(requestor.POST(action, params=params,
                                stream=True)) as response:
        for line in response.iter_lines(chunk_size=30):
            if isinstance(line, unicode):
                line = line.encode('utf-8')

            print line

    line = line.strip()
    if not any([x in line for x in expected]):
        sys.exit(3)
