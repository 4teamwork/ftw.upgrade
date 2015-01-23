from contextlib import closing
from ftw.upgrade.command.jsonapi import add_requestor_authentication_argument
from ftw.upgrade.command.jsonapi import add_site_path_argument
from ftw.upgrade.command.jsonapi import error_handling
from ftw.upgrade.command.jsonapi import with_api_requestor
import re
import sys


def valid_upgrade_step_id(value):
    if not re.match(r'^\w+@[\w\.]+:\w+$', value):
        raise ValueError(value)
    return value


def setup_argparser(commands):
    command = commands.add_parser(
        'install',
        help='Install upgrades.',
        description=install_command.__doc__)
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
    """Install upgrades.
    """

    if args.proposed:
        action = 'execute_proposed_upgrades'
        params = ()
    else:
        action = 'execute_upgrades'
        params = [('upgrades:list', name) for name in set(args.upgrades)]

    with closing(requestor.POST(action, params=params, stream=True)) as response:
        for line in response.iter_lines(chunk_size=30, decode_unicode=True):
            print line

    if line.strip() != 'Result: SUCCESS':
        sys.exit(3)
