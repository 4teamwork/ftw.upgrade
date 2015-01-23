from contextlib import closing
from ftw.upgrade.command.jsonapi import add_requestor_authentication_argument
from ftw.upgrade.command.jsonapi import add_site_path_argument
from ftw.upgrade.command.jsonapi import error_handling
from ftw.upgrade.command.jsonapi import with_api_requestor
from ftw.upgrade.command.terminal import TERMINAL
import re
import sys


DOCS = """
{t.bold}DESCRIPTION:{t.normal}
    Install upgrades. Either the "--proposed" or the "--upgrades" argument \
must be used.

{t.bold}PROPOSED UPGRADES:{t.normal}
    When using the "--proposed" argument, all proposed upgrade steps are\
 installed, ordered by dependencies and versions.

{t.bold}SET OF UPGRADES:{t.normal}
    By using the "--upgrades" argument, one or many upgrades can be \
installed. \
Each upgrade is identified by its API id of format "<dest>@<profileid>".

{t.bold}INSTALL ORDER:{t.normal}
    The upgrades are always reordered before they are installed. \
The profiles are ordered topologically with the GS profile dependency graph. \
Upgrades within each profile are ordered by the source / destination versions.

{t.bold}EXAMPLES:{t.normal}
[quote]
$ bin/upgrade install --site Plone --proposed
$ bin/upgrade install --site Plone --proposed --auth admin:admin
$ bin/upgrade install --site Plone --upgrades 3001@my.package:default \
3002@my.package:default
[/quote]

""".format(t=TERMINAL).strip()


def valid_upgrade_step_id(value):
    if not re.match(r'^\w+@[\w\.]+:\w+$', value):
        raise ValueError(value)
    return value


def setup_argparser(commands):
    command = commands.add_parser(
        'install',
        help='Install upgrades.',
        description=DOCS)
    command.set_defaults(func=install_command)
    add_requestor_authentication_argument(command)
    add_site_path_argument(command)

    group = command.add_mutually_exclusive_group(required=True)
    group.add_argument('--upgrades', '-u', nargs='+',
                       help='One or many upgrade step API ids.',
                       type=valid_upgrade_step_id)
    group.add_argument('--proposed', '-p', action='store_true',
                       help='Installs all proposed upgrades.')


@with_api_requestor
@error_handling
def install_command(args, requestor):
    if args.proposed:
        action = 'execute_proposed_upgrades'
        params = ()
    else:
        action = 'execute_upgrades'
        params = [('upgrades:list', name) for name in set(args.upgrades)]

    with closing(requestor.POST(action, params=params,
                                stream=True)) as response:
        for line in response.iter_lines(chunk_size=30, decode_unicode=True):
            print line

    if line.strip() != 'Result: SUCCESS':
        sys.exit(3)
