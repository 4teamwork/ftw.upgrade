from ftw.upgrade.command.jsonapi import add_requestor_authentication_argument
from ftw.upgrade.command.jsonapi import add_site_path_argument
from ftw.upgrade.command.jsonapi import error_handling
from ftw.upgrade.command.jsonapi import with_api_requestor
from ftw.upgrade.command.terminal import TERMINAL


DOCS = """
{t.bold}DESCRIPTION:{t.normal}
    Recook CSS and JavaScript resource bundles.
[quote]
    $ ./bin/upgrade recook --site Plone
[/quote]
""".format(t=TERMINAL).strip()


def setup_argparser(commands):
    command = commands.add_parser(
        'recook',
        help='Recook CSS and JavaScript resource bundles.',
        description=DOCS)
    command.set_defaults(func=recook_command)
    add_requestor_authentication_argument(command)
    add_site_path_argument(command)


@with_api_requestor
@error_handling
def recook_command(args, requestor):
    print(requestor.POST('recook_resources').json())
