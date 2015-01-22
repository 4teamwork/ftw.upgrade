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


def setup_argparser(commands):
    command = commands.add_parser(
        'profiles',
        help='List profiles.',
        description=list_profiles.__doc__)
    command.set_defaults(func=list_profiles)
    add_requestor_authentication_argument(command)
    add_site_path_argument(command)
    add_json_argument(command)


@with_api_requestor
@error_handling
def list_profiles(args, requestor):
    """List all Generic Setup profiles which are installed on this Plone
    site and have upgrades.
    """
    response = requestor.GET('list_profiles')

    if args.json:
        print response.text
        return

    tabledata = []
    for profile in response.json():
        tabledata.append(
            [colorize_profile_id(profile['id']),
             colorized_profile_flags(profile),
             TERMINAL.bold(profile['title']),
             colorized_profile_versions(profile)])

    print TERMINAL.bold('Installed profiles:')
    print_table(tabledata, ['ID:', '', 'Title:', 'Versions (DB/FS):'])
