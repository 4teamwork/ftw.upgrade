from __future__ import print_function
from binascii import hexlify
from ftw.upgrade.utils import get_tempfile_authentication_directory
from path import Path
from requests.auth import AuthBase
from requests.auth import HTTPBasicAuth
from requests.exceptions import HTTPError
from six.moves.urllib.parse import urlparse

import cgi
import hashlib
import hmac
import logging
import os
import re
import requests
import six
import socket
import sys
import tempfile
import time


TIMEOUT = 60


logger = logging.getLogger('ftw.upgrade')


class NoRunningInstanceFound(Exception):
    pass


class APIRequestor(object):

    def __init__(self, auth, site=None, instance_name=None):
        self.session = requests.Session()
        self.session.auth = auth
        self.site = site
        self.instance_name = instance_name

    def GET(self, action, site=None, instance_name=None, **kwargs):
        return self._make_request('GET', action, site=site,
                                  instance_name=instance_name, **kwargs)

    def POST(self, action, site=None, instance_name=None, **kwargs):
        return self._make_request('POST', action, site=site,
                                  instance_name=instance_name, **kwargs)

    def _make_request(self, method, action, site=None, instance_name=None, **kwargs):
        url = get_api_url(action, site=site or self.site,
                          instance_name=instance_name or self.instance_name)
        response = self.session.request(method.upper(), url, **kwargs)
        response.raise_for_status()
        return response


class TempfileAuth(AuthBase):
    """A requests authenticator which writes a tempfile with a random
    hash to verify that the client and the server is at the same
    machine and with the same user.
    """

    def __init__(self, relative_to=None):
        self.relative_to = relative_to

    def __call__(self, request):
        self._generate_tempfile()
        value = ':'.join((os.path.basename(self.authfile.name), self.authhash))
        request.headers['x-ftw.upgrade-tempfile-auth'] = value
        return request

    def _generate_tempfile(self):
        directory = self._get_temp_directory()
        self.authhash = hmac.new(hexlify(os.urandom(32)),
                                 hexlify(os.urandom(32)),
                                 hashlib.sha256).hexdigest()
        self.authfile = tempfile.NamedTemporaryFile(
            dir=directory)
        self.authfile.write(six.ensure_binary(self.authhash))
        self.authfile.flush()
        # Make sure the file is readable by the group, so that the service
        # user running Zope can read it even when it is not the creator.
        Path(self.authfile.name).chmod(0o640)

    def _get_temp_directory(self):
        relative_to = self.relative_to or sys.argv[0]
        return get_tempfile_authentication_directory(relative_to)


def add_requestor_authentication_argument(argparse_command):
    argparse_command.add_argument(
        '--auth',
        help='Authentication information: "<username>:<password>"')


def add_requestor_instance_argument(argparse_command):
    argparse_command.add_argument(
        '--instance',
        help='instance that should be used for all requests. '
             'If not specified the first running instance is used.')


def add_site_path_argument(argparse_command):
    argparse_command.add_argument(
        '--verbose', '-v', action='store_true',
        help='Verbose logging.')
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
    group.add_argument(
        '--all-sites', '-A', action='store_true',
        help='Perform the action on all Plone sites.')


def add_json_argument(argparse_command):
    argparse_command.add_argument('--json',
                                  action='store_true',
                                  help='Print result as JSON.')


def with_api_requestor(func):
    def func_wrapper(args):
        default_auth = os.environ.get('UPGRADE_AUTHENTICATION', None)
        auth_value = args.auth or default_auth
        if auth_value:
            if len(auth_value.split(':')) != 2:
                print('ERROR: Invalid authentication information '
                      '"{0}".'.format(auth_value))
                print('A string of form "<username>:<password>" is required.')
                sys.exit(1)
            auth = HTTPBasicAuth(*auth_value.split(':'))
        else:
            auth = TempfileAuth()

        site = get_plone_site_by_args(args, APIRequestor(auth))
        requestor = APIRequestor(
            auth, site=site, instance_name=getattr(args, 'instance', None))
        return func(args, requestor)
    func_wrapper.__name__ = func.__name__
    func_wrapper.__doc__ = func.__doc__
    return func_wrapper


def error_handling(func):
    def func_wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except NoRunningInstanceFound:
            print('ERROR: No running Plone instance detected.')
            sys.exit(1)
        except HTTPError as exc:
            try:
                response = exc.response
                mimetype = cgi.parse_header(
                    response.headers.get('Content-Type'))[0]
                if mimetype == 'application/json':
                    print(': '.join(response.json()))
                    print('>', exc.request.url)
                    print('<', response.status_code, response.reason)
                    sys.exit(1)

                raise

            except Exception as subexc:
                print('Exception while rendering error:', subexc)
                raise exc

    func_wrapper.__name__ = func.__name__
    func_wrapper.__doc__ = func.__doc__
    return func_wrapper


def get_api_url(action, site=None, instance_name=None):
    url = get_zope_url(instance_name)
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


def get_zope_url(instance_name=None):
    instance = get_running_instance(Path.getcwd(), instance_name)
    if not instance:
        raise NoRunningInstanceFound()
    return 'http://localhost:{0}/'.format(instance['port'])


def _get_running_instance(buildout_path, instance_name=None):
    for zconf in find_instance_zconfs(buildout_path, instance_name):
        port = get_instance_port(zconf)
        if not port:
            continue
        if is_port_open(port):
            return {'port': port,
                    'path': zconf.dirname().dirname()}
    return None


def get_running_instance(buildout_path, instance_name=None):
    """Because upgrades usually happen shortly after restarting the instances,
    it is possible that the instances are not yet reachable yet. We therefore
    retry to find a running instance until TIMEOUT is reached.
    """
    t0 = time.time()
    while True:
        instance_info = _get_running_instance(buildout_path, instance_name)
        if instance_info is not None or time.time()-t0 > TIMEOUT:
            break
        time.sleep(5)
    return instance_info


def find_instance_zconfs(buildout_path, instance_name=None):
    return sorted(
        buildout_path.glob('parts/{}/etc/zope.conf'.format(instance_name or "*"))
        + buildout_path.glob('parts/{}/etc/wsgi.ini'.format(instance_name or "*"))
    )


def get_instance_port(zconf):
    # zope.conf
    match = re.search(r'\saddress ([\d.]*:)?(\d+)', zconf.text())
    if match:
        return int(match.group(2))
    # wsgi.ini
    match = re.search(r'\slisten = ([\d.]*:)?(\d+)', zconf.text())
    if match:
        return int(match.group(2))
    # wsgi.ini with fast listen
    match = re.search(r'\sfast-listen = ([\d.]*:)?(\d+)', zconf.text())
    if match:
        return int(match.group(2))
    return None


def is_port_open(port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('127.0.0.1', port))
    sock.close()
    return result == 0


def get_plone_site_by_args(args, requestor):
    if getattr(args, 'site', None):
        site = args.site
        setattr(args, 'picked_site', site)
        return site
    if getattr(args, 'pick_site', False):
        sites = get_sites(requestor)
        if len(sites) != 1:
            print('ERROR: --pick-site is ambiguous:')
            print('Expected exactly one site, found', len(sites))
            sys.exit(1)
        site = sites[0]['path']
        setattr(args, 'picked_site', site)
        return site
    if getattr(args, 'last_site', False):
        sites = get_sites(requestor)
        if len(sites) == 0:
            print('ERROR: No Plone site found.')
            sys.exit(1)
        site = sites[-1]['path']
        setattr(args, 'picked_site', site)
        return site
    if getattr(args, 'all_sites', None):
        sites = get_sites(requestor)
        if len(sites) == 0:
            print('ERROR: No Plone site found.')
            sys.exit(1)
        # Get and update site index stored in the arguments.  This is used for
        # iterating over the sites one by one.
        site_index = getattr(args, 'site_index', 0)
        if site_index >= len(sites):
            raise StopIteration
        site = sites[site_index]['path']
        setattr(args, 'site_index', site_index + 1)
        setattr(args, 'picked_site', site)
        return site
    return None


def get_sites(requestor):
    response = requestor.GET('list_plone_sites')
    return response.json()
