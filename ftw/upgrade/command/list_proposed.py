from ftw.upgrade.command.jsonapi import add_json_argument
from ftw.upgrade.command.jsonapi import add_requestor_authentication_argument
from ftw.upgrade.command.jsonapi import add_site_path_argument
from ftw.upgrade.command.jsonapi import error_handling
from ftw.upgrade.command.jsonapi import with_api_requestor
from ftw.upgrade.command.terminal import print_table
from ftw.upgrade.command.terminal import TERMINAL
from ftw.upgrade.command.terminal import upgrade_id_with_flags


def setup_argparser(commands):
    command = commands.add_parser(
        'proposed',
        help='List proposed upgrades.',
        description=list_proposed.__doc__)
    command.set_defaults(func=list_proposed)
    add_requestor_authentication_argument(command)
    add_site_path_argument(command)
    add_json_argument(command)


@with_api_requestor
@error_handling
def list_proposed(args, requestor):
    """List proposed upgrades.
    """
    response = requestor.GET('list_proposed_upgrades')

    if args.json:
        print response.text
        return

    tabledata = []
    for upgrade in response.json():
        tabledata.append(
            [upgrade_id_with_flags(upgrade, omit_flags=('proposed',)),
             TERMINAL.bold(upgrade.get('title')),
             ])
    print TERMINAL.bold('Proposed upgrades:')
    print_table(tabledata, ['ID:', 'Title:'])
