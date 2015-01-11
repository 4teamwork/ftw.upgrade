from contextlib import contextmanager
from datetime import datetime
from ftw.builder import Builder
from ftw.testbrowser import browser
from ftw.testbrowser import browsing
from ftw.upgrade.directory import scaffold
from ftw.upgrade.interfaces import IUpgradeStepRecorder
from ftw.upgrade.tests.base import UpgradeTestCase
from plone.app.testing import SITE_OWNER_NAME
from Products.CMFCore.utils import getToolByName
from urllib2 import HTTPError
from zope.component import getMultiAdapter
import json
import re
import transaction
import urllib


class TestPloneSiteJsonApi(UpgradeTestCase):

    @browsing
    def test_get_profile(self, browser):
        self.package.with_profile(
            Builder('genericsetup profile')
            .with_upgrade(Builder('plone upgrade step').upgrading('1', to='2'))
            .with_upgrade(Builder('ftw upgrade step').to(datetime(2011, 1, 1))))

        with self.package_created():
            self.install_profile('the.package:default', version='1')
            self.clear_recorded_upgrades('the.package:default')

            self.api_request('GET', 'get_profile', dict(profileid='the.package:default'))
            self.assertEqual('application/json; charset=utf-8',
                             browser.headers.get('content-type'))

            self.assert_json_equal(
                {'id': 'the.package:default',
                 'title': 'the.package',
                 'product': 'the.package',
                 'db_version': '1',
                 'fs_version': '20110101000000',
                 'outdated_fs_version': False,
                 'upgrades': [

                        {'id': '2@the.package:default',
                         'title': '',
                         'source': '1',
                         'dest': '2',
                         'proposed': True,
                         'done': False,
                         'orphan': False,
                         'outdated_fs_version': False},

                        {'id': '20110101000000@the.package:default',
                         'title': 'Upgrade.',
                         'source': '2',
                         'dest': '20110101000000',
                         'proposed': True,
                         'done': False,
                         'orphan': False,
                         'outdated_fs_version': False},
                        ]},

                browser.json)

    @browsing
    def test_get_profile_requires_profileid(self, browser):
        with self.expect_api_error(status=400,
                                   message='Param missing',
                                   details='The param "profileid" is required'
                                   ' for this API action.'):
            self.api_request('GET', 'get_profile')

    @browsing
    def test_list_profiles(self, browser):
        self.package.with_profile(
            Builder('genericsetup profile')
            .with_upgrade(Builder('ftw upgrade step').to(datetime(2011, 1, 1))))
        self.package.with_profile(
            Builder('genericsetup profile')
            .named('foo')
            .with_upgrade(Builder('ftw upgrade step').to(datetime(2011, 1, 1))))

        with self.package_created():
            self.install_profile('the.package:default')
            self.install_profile('the.package:foo')

            self.api_request('GET', 'list_profiles')
            self.assertEqual('application/json; charset=utf-8',
                             browser.headers.get('content-type'))

            self.assert_json_contains_profile(
                {'id': 'the.package:default',
                 'title': 'the.package',
                 'product': 'the.package',
                 'db_version': '20110101000000',
                 'fs_version': '20110101000000',
                 'outdated_fs_version': False,
                 'upgrades': [
                        {'id': '20110101000000@the.package:default',
                         'title': 'Upgrade.',
                         'source': '10000000000000',
                         'dest': '20110101000000',
                         'proposed': False,
                         'done': True,
                         'orphan': False,
                         'outdated_fs_version': False},
                        ]},
                browser.json)

            self.assert_json_contains_profile(
                {'id': 'the.package:foo',
                 'title': 'the.package',
                 'product': 'the.package',
                 'db_version': '20110101000000',
                 'fs_version': '20110101000000',
                 'outdated_fs_version': False,
                 'upgrades': [
                        {'id': '20110101000000@the.package:foo',
                         'title': 'Upgrade.',
                         'source': '10000000000000',
                         'dest': '20110101000000',
                         'proposed': False,
                         'done': True,
                         'orphan': False,
                         'outdated_fs_version': False},
                        ]},
                browser.json)

    @browsing
    def test_list_profiles_proposing_upgrades(self, browser):
        self.package.with_profile(
            Builder('genericsetup profile')
            .with_upgrade(Builder('plone upgrade step').upgrading('1', to='2'))
            .with_upgrade(Builder('ftw upgrade step').to(datetime(2011, 1, 1))))

        with self.package_created():
            self.install_profile('the.package:default', version='2')
            self.clear_recorded_upgrades('the.package:default')

            self.api_request('GET', 'list_profiles_proposing_upgrades')
            self.assertEqual('application/json; charset=utf-8',
                             browser.headers.get('content-type'))

            self.assert_json_contains_profile(
                {'id': 'the.package:default',
                 'title': 'the.package',
                 'product': 'the.package',
                 'db_version': '2',
                 'fs_version': '20110101000000',
                 'outdated_fs_version': False,
                 'upgrades': [
                        {'id': '20110101000000@the.package:default',
                         'title': 'Upgrade.',
                         'source': '2',
                         'dest': '20110101000000',
                         'proposed': True,
                         'done': False,
                         'orphan': False,
                         'outdated_fs_version': False},
                        ]},
                browser.json)

    @browsing
    def test_execute_upgrades_installs_upgrades_in_gatherer_order(self, browser):
        self.package.with_profile(
            Builder('genericsetup profile')
            .with_upgrade(Builder('ftw upgrade step').to(datetime(2011, 1, 1))
                          .named('The first upgrade step'))
            .with_upgrade(Builder('ftw upgrade step').to(datetime(2012, 2, 2))
                          .named('The second upgrade step')))

        with self.package_created():
            self.install_profile('the.package:default', version='1')
            self.clear_recorded_upgrades('the.package:default')
            self.assertFalse(self.is_installed('the.package:default', datetime(2011, 1, 1)))
            self.assertFalse(self.is_installed('the.package:default', datetime(2012, 2, 2)))

            self.api_request('POST', 'execute_upgrades', (
                    ('upgrades:list', '20120202000000@the.package:default'),
                    ('upgrades:list', '20110101000000@the.package:default')))
            self.assertTrue(self.is_installed('the.package:default', datetime(2011, 1, 1)))
            self.assertTrue(self.is_installed('the.package:default', datetime(2012, 2, 2)))
            self.assertEqual(
                ['UPGRADE STEP the.package:default: The first upgrade step.',
                 'UPGRADE STEP the.package:default: The second upgrade step.'],
                re.findall(r'UPGRADE STEP.*', browser.contents))

    @browsing
    def test_execute_upgrades_requires_upgrades_param(self, browser):
        with self.expect_api_error(status=400,
                                   message='Param missing',
                                   details='The param "upgrades:list" is required for'
                                   ' this API action.'):
            self.api_request('POST', 'execute_upgrades', {'enforce': 'post'})

    @browsing
    def test_execute_upgrades_validates_upgrade_ids(self, browser):
        with self.expect_api_error(status=400,
                                   message='Upgrade not found',
                                   details='The upgrade "foo@bar:default" is unkown.'):
            self.api_request('POST', 'execute_upgrades', {'upgrades:list': 'foo@bar:default'})

    @browsing
    def test_execute_upgrades_not_allowed_when_plone_outdated(self, browser):
        portal_migration = getToolByName(self.layer['portal'], 'portal_migration')
        portal_migration.setInstanceVersion('1.0.0')
        transaction.commit()

        with self.expect_api_error(status=400,
                                   message='Plone site outdated',
                                   details='The Plone site is outdated and needs to'
                                   ' be upgraded first using the regular Plone'
                                   ' upgrading tools.'):
            self.api_request('POST', 'execute_upgrades', {'enforce': 'post'})

    def assert_json_equal(self, expected, got, msg=None):
        expected = json.dumps(expected, sort_keys=True, indent=4)
        got = json.dumps(got, sort_keys=True, indent=4)
        self.maxDiff = None
        self.assertMultiLineEqual(expected, got, msg)

    def assert_json_contains_profile(self, expected_profileinfo, got, msg=None):
        profileid = expected_profileinfo['id']
        got_profiles = dict([(profile['id'], profile) for profile in got])
        self.assertIn(profileid, got_profiles,
                      'assert_json_contains_profile: expected profile not in JSON')
        self.assert_json_equal(expected_profileinfo, got_profiles[profileid], msg)

    def is_installed(self, profileid, dest_time):
        recorder = getMultiAdapter((self.portal, profileid), IUpgradeStepRecorder)
        return recorder.is_installed(dest_time.strftime(scaffold.DATETIME_FORMAT))

    def api_request(self, method, action, data=()):
        browser.login(SITE_OWNER_NAME)

        if method.lower() == 'get':
            browser.visit(view='upgrades.json/{0}?{1}'.format(
                    action,
                    urllib.urlencode(data)))

        elif method.lower() == 'post':
            browser.visit(view='upgrades.json/{0}'.format(action),
                          data=data)

        else:
            raise Exception('Unsupported request method {0}'.format(method))

    @contextmanager
    def expect_api_error(self, **expectations):
        api_error_info = {}
        with self.expect_request_error() as response_info:
            yield api_error_info

        api_error_info.update(response_info)
        del api_error_info['headers']  # not serializable
        api_error_info['response_message'] = response_info['message']
        try:
            body_json = json.loads(response_info['body'])
            assert len(body_json) == 3
            assert body_json[0] == 'ERROR'
            api_error_info['message'] = body_json[1]
            api_error_info['details'] = body_json[2]
        except:
            raise AssertionError(
                'Unexpected error response body. A three item list is expected,'
                ' consisting of "ERROR", the error message (short) and the error details.\n'
                'Response body: {0}'.format(response_info['body']))

        self.assertDictContainsSubset(
            expectations, api_error_info,
            'Unexpected error response details.\n\n'
            'Expected:' +
            json.dumps(expectations, sort_keys=True, indent=4) +
            '\nto be included in:\n' +
            json.dumps(api_error_info, sort_keys=True, indent=4))

    @contextmanager
    def expect_request_error(self):
        response_info = {}
        with self.assertRaises(HTTPError) as cm:
            yield response_info

        exc = cm.exception
        response_info['status'] = exc.wrapped.code
        response_info['message'] = exc.wrapped.msg
        response_info['url'] = exc.wrapped._url
        response_info['headers'] = exc.hdrs
        response_info['body'] = exc.wrapped.read()
