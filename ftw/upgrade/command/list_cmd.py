from ftw.upgrade.command.jsonapi import add_json_argument
from ftw.upgrade.command.jsonapi import add_requestor_authentication_argument
from ftw.upgrade.command.jsonapi import add_site_path_argument
from ftw.upgrade.command.jsonapi import error_handling
from ftw.upgrade.command.jsonapi import with_api_requestor
from ftw.upgrade.command.terminal import colorize_profile_id
from ftw.upgrade.command.terminal import colorized_profile_flags
from ftw.upgrade.command.terminal import colorized_profile_versions
from ftw.upgrade.command.terminal import print_table
from ftw.upgrade.command.terminal import TERMINAL
from ftw.upgrade.command.terminal import upgrade_id_with_flags


DOCS = """
{t.bold}DESCRIPTION:{t.normal}
    List profiles or upgrades of a Plone site.

{t.bold}LIST PROFILES:{t.normal}
    Listing profiles lists all profiles which are installed on this Plone \
site and have at least one upgrade step. The profiles are listed with profile \
ID, amount of proposed and orphan upgrades for this profile, the title as \
well as database and filesystem versions.

[quote]
    $ ./bin/upgrade list --site Plone --profiles
    $ ./bin/upgrade list --site Plone --profiles --auth admin:admin
    $ ./bin/upgrade list --site Plone --profiles --auth admin:admin --json
[/quote]

{t.bold}LIST PROPOSED UPGRADES:{t.normal}
    Listing proposed upgrades lists all upgrades which are proposed for this \
Plone site. Only profiles installed on this Plone site are respected.

[quote]
    $ ./bin/upgrade list --site Plone --upgrades
    $ ./bin/upgrade list --site Plone --upgrades --auth admin:admin
    $ ./bin/upgrade list --site Plone --upgrades --auth admin:admin --json
[/quote]
""".format(t=TERMINAL).strip()


def setup_argparser(commands):
    command = commands.add_parser(
        'list',
        help='List upgrades or profiles.',
        description=DOCS)
    command.set_defaults(func=list_command)
    add_requestor_authentication_argument(command)
    add_site_path_argument(command)
    add_json_argument(command)

    group = command.add_mutually_exclusive_group(required=True)
    group.add_argument('--upgrades', '-u',
                       help='List all proposed upgrades.',
                       dest='action',
                       action='store_const',
                       const='list_proposed_upgrades')

    group.add_argument('--profiles', '-p',
                       help='List all installed profiles.',
                       dest='action',
                       action='store_const',
                       const='list_profiles')


@with_api_requestor
@error_handling
def list_command(args, requestor):
    response = requestor.GET(args.action)
    if args.json:
        print(response.text)
        return

    if args.action == 'list_proposed_upgrades':
        return format_proposed_upgrades(response)
    else:
        return format_profiles(response)


def format_proposed_upgrades(response):
    proposed = []
    for upgrade in response.json():
        is_deferrable = upgrade.get('deferrable', False)

        omit_flags = ('proposed', 'orphan') if is_deferrable else ('proposed',)

        table_row = [upgrade_id_with_flags(upgrade, omit_flags=omit_flags),
                     TERMINAL.bold(upgrade.get('title')),
                     ]
        proposed.append(table_row)

    print(TERMINAL.bold('Proposed upgrades:'))
    print_table(proposed, ['ID:', 'Title:'])


def format_profiles(response):
    tabledata = []
    for profile in response.json():
        tabledata.append(
            [colorize_profile_id(profile['id']),
             colorized_profile_flags(profile),
             TERMINAL.bold(profile['title']),
             colorized_profile_versions(profile)])

    print(TERMINAL.bold('Installed profiles:'))
    print_table(tabledata, ['ID:', '', 'Title:', 'Versions (DB/FS):'])
