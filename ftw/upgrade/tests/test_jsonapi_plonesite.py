from datetime import datetime
from ftw.builder import Builder
from ftw.testbrowser import browsing
from ftw.upgrade.tests.base import JsonApiTestCase
from Products.CMFCore.utils import getToolByName
import re
import transaction


class TestPloneSiteJsonApi(JsonApiTestCase):

    @browsing
    def test_api_discovery(self, browser):
        self.api_request('GET', '')

        self.assert_json_equal(
            {'api_version': 'v1',
             'actions':
                 [{'name': 'execute_proposed_upgrades',
                   'required_params': [],
                   'description': 'Executes all proposed upgrades.',
                   'request_method': 'POST'},

                  {'name': 'execute_upgrades',
                   'required_params': ['upgrades:list'],
                   'description': 'Executes a list of upgrades, each identified by'
                   ' the upgrade ID in the form "[dest-version]@[profile ID]".',
                   'request_method': 'POST'},

                  {'name': 'get_profile',
                   'required_params': ['profileid'],
                   'description': 'Returns the profile with the id "profileid" as hash.',
                   'request_method': 'GET'},

                  {'name': 'list_profiles',
                   'required_params': [],
                   'description': 'Returns a list of all installed profiles.',
                   'request_method': 'GET'},

                  {'name': 'list_profiles_proposing_upgrades',
                   'required_params': [],
                   'description': 'Returns a list of profiles with proposed upgrade steps.'
                   ' The upgrade steps of each profile only include proposed upgrades.',
                   'request_method': 'GET'},

                  {'name': 'list_proposed_upgrades',
                   'required_params': [],
                   'description': 'Returns a list of proposed upgrades.',
                   'request_method': 'GET'},

                  {'name': 'recook_resources',
                   'required_params': [],
                   'description': 'Recook CSS and JavaScript resource bundles.',
                   'request_method': 'POST'}]},

            browser.json)

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
    def test_get_profile_requires_GET(self, browser):
        with self.expect_api_error(status=405,
                                   message='Method Not Allowed',
                                   details='Action requires GET') as cm:
            self.api_request('POST', 'get_profile', {'profileid': 'the.package:default'})
        self.assertEquals('GET', cm['headers'].get('allow'))

    @browsing
    def test_get_unkown_profile_returns_error(self, browser):
        with self.expect_api_error(status=400,
                                   message='Profile not found',
                                   details='The profile "something:default" is wrong'
                                   ' or not installed on this Plone site.'):
            self.api_request('GET', 'get_profile', {'profileid': 'something:default'})

    @browsing
    def test_cyclic_dependency_errors_are_handled(self, browser):
        self.package.with_profile(Builder('genericsetup profile')
                                  .named('foo')
                                  .with_upgrade(self.default_upgrade())
                                  .with_dependencies('the.package:bar'))

        self.package.with_profile(Builder('genericsetup profile')
                                  .named('bar')
                                  .with_upgrade(self.default_upgrade())
                                  .with_dependencies('the.package:foo'))

        with self.package_created():
            self.install_profile('the.package:foo')
            self.install_profile('the.package:bar')

            with self.expect_api_error(status=500,
                                       message='Cyclic dependencies',
                                       details='There are cyclic Generic Setup profile'
                                       ' dependencies.'):
                self.api_request('GET', 'get_profile', {'profileid': 'the.package:foo'})

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
    def test_list_profiles_requires_authentication(self, browser):
        with self.expect_api_error(status=401,
                                   message='Unauthorized',
                                   details='Admin authorization required.'):
            self.api_request('GET', 'list_profiles', authenticate=False)

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
    def test_list_proposed_upgrades_when_empty(self, browser):
        self.api_request('GET', 'list_proposed_upgrades')
        self.assertEqual('application/json; charset=utf-8',
                         browser.headers.get('content-type'))

    @browsing
    def test_list_proposed_upgrdes(self, browser):
        self.package.with_profile(
            Builder('genericsetup profile')
            .with_upgrade(Builder('plone upgrade step').upgrading('1', to='2')))

        self.package.with_profile(
            Builder('genericsetup profile')
            .named('foo')
            .with_upgrade(Builder('plone upgrade step').upgrading('2', to='3')))

        with self.package_created():
            self.install_profile('the.package:default', version='1')
            self.install_profile('the.package:foo', version='1')

            self.api_request('GET', 'list_proposed_upgrades')
            self.assertEqual('application/json; charset=utf-8',
                             browser.headers.get('content-type'))

            self.assert_json_contains(
                {'id': '2@the.package:default',
                 'title': '',
                 'source': '1',
                 'dest': '2',
                 'proposed': True,
                 'done': False,
                 'orphan': False,
                 'outdated_fs_version': False},
                browser.json)

            self.assert_json_contains(
                {'id': '3@the.package:foo',
                 'title': '',
                 'source': '2',
                 'dest': '3',
                 'proposed': True,
                 'done': False,
                 'orphan': False,
                 'outdated_fs_version': False},
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

            self.assertIn('Result: SUCCESS', browser.contents)

    @browsing
    def test_execute_upgrades_requires_upgrades_param(self, browser):
        with self.expect_api_error(status=400,
                                   message='Param missing',
                                   details='The param "upgrades:list" is required for'
                                   ' this API action.'):
            self.api_request('POST', 'execute_upgrades')

    @browsing
    def test_execute_upgrades_validates_upgrade_ids(self, browser):
        with self.expect_api_error(status=400,
                                   message='Upgrade not found',
                                   details='The upgrade "foo@bar:default" is unkown.'):
            self.api_request('POST', 'execute_upgrades', {'upgrades:list': 'foo@bar:default'})

    @browsing
    def test_execute_upgrades_requires_POST(self, browser):
        with self.expect_api_error(status=405,
                                   message='Method Not Allowed',
                                   details='Action requires POST') as cm:
            self.api_request('GET', 'execute_upgrades', {'upgrades:list': 'foo@bar:default'})
        self.assertEquals('POST', cm['headers'].get('allow'))

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
            self.api_request('POST', 'execute_upgrades', {'upgrades:list': 'foo@bar:default'})

    @browsing
    def test_execute_proposed_upgrades(self, browser):
        self.package.with_profile(
            Builder('genericsetup profile')
            .with_upgrade(Builder('ftw upgrade step').to(datetime(2011, 1, 1))
                          .named('The upgrade')))

        with self.package_created():
            self.install_profile('the.package:default', version='2')
            self.clear_recorded_upgrades('the.package:default')

            self.assertFalse(self.is_installed('the.package:default', datetime(2011, 1, 1)))
            self.api_request('POST', 'execute_proposed_upgrades')
            self.assertTrue(self.is_installed('the.package:default', datetime(2011, 1, 1)))

            self.assertIn('UPGRADE STEP the.package:default: The upgrade.',
                          browser.contents)
            self.assertIn('Result: SUCCESS', browser.contents)

    @browsing
    def test_executing_upgrades_with_failure_results_in_error_result(self, browser):
        def failing_upgrade(setup_context):
            raise KeyError('foo')

        self.package.with_profile(
            Builder('genericsetup profile')
            .with_upgrade(Builder('plone upgrade step')
                          .upgrading('1', to='2')
                          .calling(failing_upgrade)))

        with self.package_created():
            self.install_profile('the.package:default', version='1')
            self.api_request('POST', 'execute_proposed_upgrades')
            self.assertIn('Result: FAILURE', browser.contents)

    @browsing
    def test_recook_resources(self, browser):
        with self.assert_resources_recooked():
            self.api_request('POST', 'recook_resources')
            self.assertEqual('OK', browser.json)
