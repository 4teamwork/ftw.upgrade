from argparse import HelpFormatter
from requests.exceptions import ConnectionError
import argparse
import json
import requests
import shlex
import sys
from ftw.upgrade.utils import join_lines


class Log(object):
    def error(self, msg):
        sys.stderr.write(msg + '\n')

log = Log()


class UpgradeCommand(object):
    def __init__(self, zopectl_cmd, args):
        self.options = zopectl_cmd.options
        self.args = args

    def _parse_args(self, args):
        arglist = shlex.split(args)
        prog = "%s %s" % (self.options.progname, sys.argv[1])

        # Top level parser
        formatter = lambda prog: HelpFormatter(prog, max_help_position=30)
        parser = argparse.ArgumentParser(prog=prog,
                                         formatter_class=formatter)

        # Global arguments
        parser.add_argument(
            '-v',
            '--verbose',
            action='store_true',
            help='Be very verbose.')

        parser.add_argument(
            '-j',
            '--json',
            action='store_true',
            help='Produce machine readable JSON output. Default is human '
                 'readable.')

        # Commands
        #
        # TODO: short forms for commands, probably needs a hack
        subparsers = parser.add_subparsers(
            title='Upgrade commands',
            dest='cmd',
            metavar="<command>",
            description="(use <cmd> -h to get details about a command's "
                        "options)")

        # "list-sites" command
        ls = subparsers.add_parser(
            'list-sites',
            help='List all Plone sites')

        ls.add_argument('-u',
                        '--upgradable',
                        required=False,
                        action='store_true',
                        help='Only list sites that can and need to be '
                             'upgraded')

        # "list-upgrades" command
        lu = subparsers.add_parser(
            'list-upgrades',
            help='List upgrades for one or more Plone sites')

        lu.add_argument('-s',
                        '--site',
                        required=False,
                        type=str,
                        help='Plone Site ID')

        lu.add_argument('-a',
                        '--all',
                        required=False,
                        action='store_true',
                        help='List all upgrades (default is to list only proposed)')

        # "run-all-upgrades" command
        rau = subparsers.add_parser(
            'run-all-upgrades',
            help='Run proposed upgrades for all Plone sites')

        rau.add_argument('--progress',
                         required=False,
                         action='store_true',
                         help='Display detailed upgrade progress')

        return parser.parse_args(arglist)


class UpgradeHTTP(UpgradeCommand):

    def run(self):
        """
        plone.recipe.zope2instance.ctl entry point handler that connects to a
        running instance.

        self
            An instance of plone.recipe.zope2instance.ctl.AdjustedZopeCmd.
        self.args
            Any additional arguments that were passed on the command line.
        """

        options = self._parse_args(self.args)
        print "Upgrading via HTTP..."

        # The zope2instance recipe only creates one HTTP server for each
        # instance
        server = self.options.configroot.servers[0]
        progname = self.options.progname

        # Determine upgrade API URL
        port = server.port
        ip = server.ip or '127.0.0.1'
        url = 'http://%s:%s/@@upgrade-api' % (ip, port)

        try:
            if options.cmd == 'list-upgrades':
                url = "%s/list_upgrades" % url
                params = {'site': options.site,
                          'proposed': not(options.all)}
                response = requests.get(url, params=params)

                if options.json:
                    print response.content
                else:
                    sites = json.loads(response.content)
                    formatter = UpgradeFormatter(sites)
                    print formatter.format()

            elif options.cmd == 'list-sites':
                url = "%s/list_sites" % url
                params = {'upgradable': options.upgradable}
                response = requests.get(url, params=params)
                print response.content

            elif options.cmd == 'run-all-upgrades':
                url = "%s/run_all_upgrades" % url
                params = {'progress': options.progress}
                response = requests.get(url, params=params)
                print response.content

            else:
                raise Exception("Unknown command '%s'" % options.cmd)


            if response.status_code == 404:
                log.error("HTTP upgrade API not found at %s" % url)
                log.error("404 Not Found")
                log.error("Make sure ftw.upgrade is installed for %s"
                                                                % progname)

        except ConnectionError, e:
            log.error("Error connecting to the HTTP upgrade API at %s" % url)
            log.error(str(e))
            log.error("Make sure %s is running." % progname)


def upgrade_handler(app, args):
    """
    zopectl.command entry point handler.

    app
        The Zope Application Root object.
    args
        Any additional arguments that were passed on the command line.
    """
    print "Upgrading..."


def upgrade_http_handler(cmd, args):
    """
    plone.recipe.zope2instance.ctl entry point handler that connects to a
    running instance.

    cmd
        An instance of plone.recipe.zope2instance.ctl.AdjustedZopeCmd.
    args
        Any additional arguments that were passed on the command line.
    """
    http_upgrade_cmd = UpgradeHTTP(cmd, args)
    http_upgrade_cmd.run()



class UpgradeFormatter(object):

    def __init__(self, sites):
        self.sites = sites

    @join_lines
    def format(self):
        for site_id, profiles in self.sites.items():
            yield "Site: %s" % site_id
            yield "=" * 74

            if profiles == []:
                yield '[No proposed upgrades]'
                return

            yield ''
            for profile in profiles:
                yield "    %s (FS: %s, DB: %s)" % (profile['id'].ljust(40),
                                                   profile['version'],
                                                   profile['db_version'])
                yield "    " + "-" * 70
                for upgrade in profile['upgrades']:
                    yield "      * %s -> %s    %s" % (
                        upgrade['ssource'], upgrade['sdest'], upgrade['title'])
                yield ''