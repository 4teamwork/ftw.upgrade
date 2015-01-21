from ftw.upgrade.command.jsonapi import add_json_argument
from ftw.upgrade.command.jsonapi import add_requestor_authentication_argument
from ftw.upgrade.command.jsonapi import error_handling
from ftw.upgrade.command.jsonapi import with_api_requestor


def setup_argparser(commands):
    command = commands.add_parser(
        'sites',
        help='Discover Plone sites.',
        description=sites_command.__doc__)
    command.set_defaults(func=sites_command)
    add_requestor_authentication_argument(command)
    add_json_argument(command)


@with_api_requestor
@error_handling
def sites_command(args, requestor):
    """Discover Plone sites on the current installation.
    """
    response = requestor.GET('list_plone_sites')

    if args.json:
        print response.text
    else:
        for site in response.json():
            print site['path'].ljust(20), site['title']
