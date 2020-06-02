from ftw.upgrade.command.jsonapi import APIRequestor
from ftw.upgrade.command.jsonapi import get_api_url
from ftw.upgrade.command.jsonapi import get_instance_port
from ftw.upgrade.command.jsonapi import get_running_instance
from ftw.upgrade.command.jsonapi import get_zope_url
from ftw.upgrade.command.jsonapi import NoRunningInstanceFound
from ftw.upgrade.command.jsonapi import TempfileAuth
from ftw.upgrade.tests.base import CommandAndInstanceTestCase
from plone.app.testing import SITE_OWNER_NAME
from plone.app.testing import TEST_USER_PASSWORD
from Products.CMFPlone.utils import safe_unicode
from requests.auth import HTTPBasicAuth
from requests.exceptions import HTTPError
from six.moves import map

import os


class ZopeConfPathStub(object):
    """Stubs a path.py Path object for a zope.conf file.
    """

    def __init__(self, *lines):
        self._text = '\n'.join(map(safe_unicode, lines))

    def text(self):
        return self._text


class TestAPIRequestor(CommandAndInstanceTestCase):

    def setUp(self):
        super(TestAPIRequestor, self).setUp()
        self.write_zconf_with_test_instance()

    def test_GET(self):
        requestor = APIRequestor(HTTPBasicAuth(SITE_OWNER_NAME, TEST_USER_PASSWORD))
        jsondata = requestor.GET('list_plone_sites').json()
        self.assertEqual([{u'id': u'plone',
                           u'path': u'/plone',
                           u'title': u'Plone site'}],
                         jsondata)

    def test_GET_raises_error(self):
        requestor = APIRequestor(HTTPBasicAuth(SITE_OWNER_NAME, TEST_USER_PASSWORD))
        with self.assertRaises(HTTPError) as cm:
            requestor.GET('wrong_action')

        self.assertEqual([u'ERROR',
                          u'Unkown API action',
                          u'There is no API action "wrong_action".'],
            cm.exception.response.json())

    def test_GET_with_params(self):
        requestor = APIRequestor(HTTPBasicAuth(SITE_OWNER_NAME, TEST_USER_PASSWORD),
                                 site='plone')

        requestor.GET('get_profile', site='plone',
                      params={'profileid': 'plone.app.discussion:default'})

    def test_error_when_no_running_instance_found(self):
        self.layer['root_path'].joinpath('parts/instance').rmtree()
        requestor = APIRequestor(HTTPBasicAuth(SITE_OWNER_NAME, TEST_USER_PASSWORD))
        with self.assertRaises(NoRunningInstanceFound):
            requestor.GET('list_plone_sites')

    def test_basic_authentication(self):
        requestor = APIRequestor(HTTPBasicAuth(SITE_OWNER_NAME, TEST_USER_PASSWORD))
        jsondata = requestor.GET('current_user').json()
        self.assertEqual('admin', jsondata)

    def test_tempfile_authentication(self):
        requestor = APIRequestor(TempfileAuth(relative_to=os.getcwd()))
        jsondata = requestor.GET('current_user').json()
        self.assertEqual('system-upgrade', jsondata)


class TestJsonAPIUtils(CommandAndInstanceTestCase):

    def test_get_api_url(self):
        self.write_zconf_with_test_instance()
        test_instance_port = self.layer['port']

        self.assertEqual(
            'http://localhost:{0}/upgrades-api/foo'.format(test_instance_port),
            get_api_url('foo'))

        self.assertEqual(
            'http://localhost:{0}/Plone/upgrades-api/bar'.format(test_instance_port),
            get_api_url('bar', site='Plone'))

        self.assertEqual(
            'http://localhost:{0}/Plone/upgrades-api/baz'.format(test_instance_port),
            get_api_url('baz', site='/Plone/'))

    def test_get_api_url_with_public_url(self):
        self.write_zconf_with_test_instance()
        test_instance_port = self.layer['port']

        os.environ['UPGRADE_PUBLIC_URL'] = 'http://domain.com'
        self.assertEqual(
            'http://localhost:{0}/'
            'VirtualHostBase/http/domain.com:80/mount-point/platform/'
            'VirtualHostRoot/upgrades-api/action'.format(test_instance_port),
            get_api_url('action', site='mount-point/platform'))

        os.environ['UPGRADE_PUBLIC_URL'] = 'https://domain.com'
        self.assertEqual(
            'http://localhost:{0}/'
            'VirtualHostBase/https/domain.com:443/mount-point/platform/'
            'VirtualHostRoot/upgrades-api/action'.format(test_instance_port),
            get_api_url('action', site='mount-point/platform'))

        os.environ['UPGRADE_PUBLIC_URL'] = 'https://domain.com/'
        self.assertEqual(
            'http://localhost:{0}/'
            'VirtualHostBase/https/domain.com:443/mount-point/platform/'
            'VirtualHostRoot/upgrades-api/action'.format(test_instance_port),
            get_api_url('action', site='mount-point/platform'))

        os.environ['UPGRADE_PUBLIC_URL'] = 'https://domain.com/foo'
        self.assertEqual(
            'http://localhost:{0}/'
            'VirtualHostBase/https/domain.com:443/mount-point/platform/'
            'VirtualHostRoot/_vh_foo/upgrades-api/action'.format(test_instance_port),
            get_api_url('action', site='mount-point/platform'))

    def test_get_zope_url_without_zconf(self):
        with self.assertRaises(NoRunningInstanceFound):
            get_zope_url()

    def test_find_first_running_instance_info(self):
        test_instance_port = self.layer['port']
        self.write_zconf('instance1', '1000')
        part2 = self.write_zconf('instance2', test_instance_port)
        self.assertEqual(
            {'port': test_instance_port,
             'path': str(part2)},
            get_running_instance(self.layer['root_path']))

    def test_find_first_running_instance_info_with_network_interface(self):
        test_instance_port = self.layer['port']
        self.write_zconf('instance1', '1000')
        part2 = self.write_zconf('instance2',
                                 '0.0.0.0:{0}'.format(test_instance_port))
        self.assertEqual(
            {'port': test_instance_port,
             'path': str(part2)},
            get_running_instance(self.layer['root_path']))

    def test_find_first_running_instance_info_named_zeoclient(self):
        test_zeoclient_port = self.layer['port']
        self.write_zconf('zeoclient1', '1000')
        part2 = self.write_zconf('zeoclient2', test_zeoclient_port)
        self.assertEqual(
            {'port': test_zeoclient_port,
             'path': str(part2)},
            get_running_instance(self.layer['root_path']))

    def test_get_instance_port_port_only(self):
        zconf = ZopeConfPathStub('<http-server>',
                                 '  address 8080',
                                 '</http-server>')
        self.assertEqual(8080, get_instance_port(zconf))

    def test_get_instance_port_localhost_interface_prefix(self):
        zconf = ZopeConfPathStub('<http-server>',
                                 '  address 127.0.0.1:8080',
                                 '</http-server>')
        self.assertEqual(8080, get_instance_port(zconf))

    def test_get_instance_port_public_interface_prefix(self):
        zconf = ZopeConfPathStub('<http-server>',
                                 '  address 127.0.0.1:8080',
                                 '</http-server>')
        self.assertEqual(8080, get_instance_port(zconf))

    def test_get_instance_port_localhost_ip(self):
        zconf = ZopeConfPathStub('ip-address 127.0.0.1',
                                 '<http-server>',
                                 '  address 127.0.0.1:8080',
                                 '</http-server>')
        self.assertEqual(8080, get_instance_port(zconf))

    def test_get_instance_port_public_ip(self):
        zconf = ZopeConfPathStub('ip-address 0.0.0.0',
                                 '<http-server>',
                                 '  address 127.0.0.1:8080',
                                 '</http-server>')
        self.assertEqual(8080, get_instance_port(zconf))

    def test_get_instance_port_no_indent(self):
        zconf = ZopeConfPathStub('<http-server>',
                                 'address 8080',
                                 '</http-server>')
        self.assertEqual(8080, get_instance_port(zconf))

    def test_get_instance_port_not_found(self):
        zconf = ZopeConfPathStub('<http-server>',
                                 '</http-server>')
        self.assertEqual(None, get_instance_port(zconf))

    def test_get_instance_port_wsgi_listen(self):
        zconf = ZopeConfPathStub('[server:main]\n'
                                 'listen = 127.0.0.1:8080')
        self.assertEqual(8080, get_instance_port(zconf))

    def test_get_instance_port_wsgi_fast_listen(self):
        zconf = ZopeConfPathStub('[server:main]\n'
                                 'fast-listen = 0.0.0.0:8080')
        self.assertEqual(8080, get_instance_port(zconf))
