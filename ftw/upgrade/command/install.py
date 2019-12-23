from __future__ import print_function
from contextlib import closing
from ftw.upgrade.command.jsonapi import add_requestor_authentication_argument
from ftw.upgrade.command.jsonapi import add_site_path_argument
from ftw.upgrade.command.jsonapi import error_handling
from ftw.upgrade.command.jsonapi import with_api_requestor
from ftw.upgrade.command.terminal import TERMINAL

import re
import six
import sys


DOCS = """
{t.bold}DESCRIPTION:{t.normal}
    Install upgrades or profiles. Either the "--proposed" or the \
    "--upgrades" or the "--profiles" argument must be used.

{t.bold}PROPOSED UPGRADES:{t.normal}
    When using the "--proposed" argument, all proposed upgrade steps are\
 installed, ordered by dependencies and versions.

{t.bold}INSTALL PROPOSED UPGRADES OF SPECIFIC PROFILES:{t.normal}
    The "--proposed" argument optionally accepts a list of profiles, \
for which proposed upgrades are installed. \
When no profile is specified, all proposed upgrades of all profiles \
are installed.

{t.bold}SET OF UPGRADES:{t.normal}
    By using the "--upgrades" argument, one or many upgrades can be \
installed. \
Each upgrade is identified by its API id of format "<dest>@<profileid>".

{t.bold}INSTALL PROFILES:{t.normal}
    By using the "--profiles" argument, one or many profiles can be \
    installed. Each install is identified by profile id.

{t.bold}INSTALL ORDER:{t.normal}
    The upgrades are always reordered before they are installed. \
The profiles are ordered topologically with the GS profile dependency graph. \
Upgrades within each profile are ordered by the source / destination versions.

{t.bold}EXAMPLES:{t.normal}
[quote]
$ bin/upgrade install --site Plone --proposed
$ bin/upgrade install --site Plone --proposed --auth admin:admin
$ bin/upgrade install --site Plone --proposed my.package:default other.package:default
$ bin/upgrade install --site Plone --upgrades 3001@my.package:default \
3002@my.package:default
$ bin/upgrade install --site Plone --profiles Products.PloneFormGen:default \
unwanted.addon:uninstall
[/quote]

""".format(t=TERMINAL).strip()


def valid_upgrade_step_id(value):
    if not re.match(r'^\w+@[\w\.]+:\w+$', value):
        raise ValueError(value)
    return value


def valid_profile_id(value):
    if ':' not in value:
        raise ValueError(value)
    return value


def setup_argparser(commands):
    command = commands.add_parser(
        'install',
        help='Install upgrades or profiles.',
        description=DOCS)
    command.set_defaults(func=install_command)
    add_requestor_authentication_argument(command)
    add_site_path_argument(command)

    command.add_argument('--force', '-f', action='store_true',
                         dest='force_reinstall',
                         default=False,
                         help='Force reinstall already installed profiles.')

    group = command.add_mutually_exclusive_group(required=True)
    group.add_argument('--upgrades', '-u', nargs='+',
                       help='One or many upgrade step API ids.',
                       type=valid_upgrade_step_id,
                       metavar='UPGRADE-STEP')
    group.add_argument('--proposed', '-p', nargs='*',
                       help='Installs all proposed upgrades of all or specific profiles.',
                       metavar='PROFILE')
    group.add_argument('--profiles', nargs='+',
                       help='One or many profile ids.',
                       type=valid_profile_id,
                       metavar='PROFILE')

    command.add_argument('--skip-deferrable', '-D',
                         help='Do not propose deferrable upgrades. Only takes '
                              'effect if specified in combination with '
                              '--proposed.',
                         default=False,
                         dest='skip_deferrable',
                         action='store_true')

    command.add_argument('--allow-outdated',
                         help='Allow installing on outdated Plone site. '
                              'By default we do not allow this, '
                              'because it is better to first run the '
                              'plone_upgrade command.',
                         default=False,
                         dest='allow_outdated',
                         action='store_true')


@with_api_requestor
@error_handling
def install_command(args, requestor):
    if args.force_reinstall and not args.profiles:
        print('ERROR: --force can only be used with --profiles.', file=sys.stderr)
        sys.exit(3)

    if args.proposed is not None:
        action = 'execute_proposed_upgrades'
        params = [('profiles:list', name) for name in args.proposed]
        if args.skip_deferrable:
            params.append(('propose_deferrable', False))
    elif args.profiles:
        action = 'execute_profiles'
        params = [('profiles:list', name) for name in set(args.profiles)]
        if args.force_reinstall:
            params.append(('force_reinstall', True))
    else:
        action = 'execute_upgrades'
        params = [('upgrades:list', name) for name in set(args.upgrades)]
    if args.allow_outdated:
        params.append(('allow_outdated', True))

    with closing(requestor.POST(action, params=params,
                                stream=True)) as response:
        for line in response.iter_lines(chunk_size=30):
            line = six.ensure_str(line)

            print(line)

    if line.strip() != 'Result: SUCCESS':
        sys.exit(3)
