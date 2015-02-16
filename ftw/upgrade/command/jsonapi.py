from path import Path
from requests.exceptions import HTTPError
from urlparse import urlparse
import cgi
import os
import re
import requests
import socket
import sys


class NoRunningInstanceFound(Exception):
    pass


class APIRequestor(object):

    def __init__(self, username, password, site=None):
        self.session = requests.Session()
        self.session.auth = (username, password)
        self.site = site

    def GET(self, action, site=None, **kwargs):
        return self._make_request('GET', action, site=site, **kwargs)

    def POST(self, action, site=None, **kwargs):
        return self._make_request('POST', action, site=site, **kwargs)

    def _make_request(self, method, action, site=None, **kwargs):
        url = get_api_url(action, site=site or self.site)
        response = self.session.request(method.upper(), url, **kwargs)
        response.raise_for_status()
        return response


def add_requestor_authentication_argument(argparse_command):
    argparse_command.add_argument(
        '--auth',
        help='Authentication information: "<username>:<password>"')


def add_site_path_argument(argparse_command):
    group = argparse_command.add_mutually_exclusive_group(required=True)
    group.add_argument(
        '--site', '-s',
        help='Path to the Plone site.')
    group.add_argument(
        '--pick-site', '-S', action='store_true',
        help='Automatically pick the Plone site, when there is exactly one.')
    group.add_argument(
        '--last-site', '-L', action='store_true',
        help='Automatically pick the last Plone site ordered by path.')


def add_json_argument(argparse_command):
    argparse_command.add_argument('--json',
                                  action='store_true',
                                  help='Print result as JSON.')


def with_api_requestor(func):
    def func_wrapper(args):
        default_auth = os.environ.get('UPGRADE_AUTHENTICATION', None)
        auth_value = args.auth or default_auth
        if not auth_value:
            print 'ERROR: No authentication information provided.'
            print 'Use either the --auth param or the UPGRADE_AUTHENTICATION' + \
                ' environment variable for providing authentication information' + \
                ' in the form "<username>:<password>".'
            sys.exit(1)

        if len(auth_value.split(':')) != 2:
            print 'ERROR: Invalid authentication information "{0}".'.format(
                auth_value)
            print 'A string of form "<username>:<password>" is required.'
            sys.exit(1)

        site = get_plone_site_by_args(args, auth_value)
        requestor = APIRequestor(*auth_value.split(':'), site=site)
        return func(args, requestor)
    func_wrapper.__name__ = func.__name__
    func_wrapper.__doc__ = func.__doc__
    return func_wrapper


def error_handling(func):
    def func_wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except NoRunningInstanceFound:
            print 'ERROR: No running Plone instance detected.'
            sys.exit(1)
        except HTTPError, exc:
            try:
                response = exc.response
                mimetype = cgi.parse_header(
                    response.headers.get('Content-Type'))[0]
                if mimetype == 'application/json':
                    print ': '.join(response.json())
                    print '>', exc.request.url
                    print '<', response.status_code, response.reason
                    sys.exit(1)

                raise

            except Exception, subexc:
                print 'Exception while rendering error:', subexc
                raise exc

    func_wrapper.__name__ = func.__name__
    func_wrapper.__doc__ = func.__doc__
    return func_wrapper


def get_api_url(action, site=None):
    url = get_zope_url()
    public_url = os.environ.get('UPGRADE_PUBLIC_URL', None)
    if public_url:
        url = extend_url_with_virtualhost_config(url, public_url, site)
    elif site:
        url += site.rstrip('/').strip('/') + '/'
    url += 'upgrades-api/'
    url += action
    return url


def extend_url_with_virtualhost_config(zope_url, public_url, site):
    urlinfo = urlparse(public_url)
    # a port is required for the virtual host monster to work nicely.
    if not urlinfo.port:
        ports = {'http': 80, 'https': 443}
        urlinfo = urlinfo._replace(netloc='{0}:{1}'.format(
                urlinfo.hostname,
                ports[urlinfo.scheme]))

    url = zope_url.rstrip('/')
    url += '/VirtualHostBase'
    url += '/' + urlinfo.scheme
    url += '/' + urlinfo.netloc
    if site:
        url += '/' + site.strip('/')
    url += '/VirtualHostRoot'
    for name in urlinfo.path.split('/'):
        if not name:
            continue
        url += '/_vh_' + name
    url += '/'
    return url


def get_zope_url():
    instance = get_running_instance(Path.getcwd())
    if not instance:
        raise NoRunningInstanceFound()
    return 'http://localhost:{0}/'.format(instance['port'])


def get_running_instance(buildout_path):
    for zconf in find_instance_zconfs(buildout_path):
        port = get_instance_port(zconf)
        if not port:
            continue
        if is_port_open(port):
            return {'port': port,
                    'path': zconf.dirname().dirname()}
    return None


def find_instance_zconfs(buildout_path):
    return sorted(buildout_path.glob('parts/instance*/etc/zope.conf'))


def get_instance_port(zconf):
    match = re.search(r'address (\d+)', zconf.text())
    if match:
        return int(match.group(1))
    return None


def is_port_open(port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('127.0.0.1', port))
    return result == 0


def get_plone_site_by_args(args, auth_value):
    if getattr(args, 'site', None):
        return args.site
    if getattr(args, 'pick_site', False):
        sites = get_sites(auth_value)
        if len(sites) != 1:
            print 'ERROR: --pick-site is ambiguous:'
            print 'Expected exactly one site, found', len(sites)
            sys.exit(1)
        return sites[0]['path']
    if getattr(args, 'last_site', False):
        sites = get_sites(auth_value)
        if len(sites) == 0:
            print 'ERROR: No Plone site found.'
            sys.exit(1)
        return sites[-1]['path']
    return None


def get_sites(auth_value):
    requestor = APIRequestor(*auth_value.split(':'))
    response = requestor.GET('list_plone_sites')
    return response.json()
