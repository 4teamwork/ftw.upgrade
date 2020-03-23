from ftw.upgrade.command.jsonapi import add_requestor_authentication_argument
from ftw.upgrade.command.jsonapi import add_site_path_argument
from ftw.upgrade.command.jsonapi import error_handling
from ftw.upgrade.command.jsonapi import with_api_requestor
from ftw.upgrade.command.terminal import TERMINAL


DOCS = """
{t.bold}DESCRIPTION:{t.normal}
    Combine JS/CSS bundles together (Plone 5).
[quote]
    $ ./bin/upgrade combine_bundles --site Plone
[/quote]
""".format(
    t=TERMINAL
).strip()


def setup_argparser(commands):
    command = commands.add_parser(
        'combine_bundles', help='Combine JS/CSS bundles together (Plone 5).', description=DOCS
    )
    command.set_defaults(func=combine_bundles)
    add_requestor_authentication_argument(command)
    add_site_path_argument(command)


@with_api_requestor
@error_handling
def combine_bundles(args, requestor):
    print((requestor.POST('combine_bundles').json()))
