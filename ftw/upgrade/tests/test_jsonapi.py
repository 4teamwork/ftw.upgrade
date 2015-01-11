from datetime import datetime
from ftw.builder import Builder
from ftw.testbrowser import browser
from ftw.testbrowser import browsing
from ftw.upgrade.tests.base import UpgradeTestCase
from plone.app.testing import SITE_OWNER_NAME
from ZPublisher import BadRequest
import json
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

            self.api_request('GET', 'get_profile', profileid='the.package:default')

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
        with self.assertRaises(BadRequest) as cm:
            self.api_request('GET', 'get_profile')

        self.assertIn('The parameter, <em>profileid</em>,'
                      ' was omitted from the request.',
                      str(cm.exception))

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

    def api_request(self, method, action, **data):
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
