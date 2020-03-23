from datetime import datetime
from ftw.builder import Builder
from ftw.upgrade import UpgradeStep
from ftw.upgrade.exceptions import CyclicDependencies
from ftw.upgrade.exceptions import UpgradeNotFound
from ftw.upgrade.gatherer import extend_auto_upgrades_with_human_formatted_date_version
from ftw.upgrade.gatherer import UpgradeInformationGatherer
from ftw.upgrade.interfaces import IUpgradeInformationGatherer
from ftw.upgrade.tests.base import UpgradeTestCase
from Products.CMFPlone.utils import getFSVersionTuple
from unittest import TestCase
from zope.component import queryAdapter
from zope.component import getMultiAdapter
from zope.interface.verify import verifyClass


class NotDeferrableUpgrade(UpgradeStep):
    """Test that attribute value is used, not attribtue presence."""

    deferrable = False

    def __call__(self):
        pass


class TestUpgradeInformationGatherer(UpgradeTestCase):

    def test_implements_interface(self):
        verifyClass(IUpgradeInformationGatherer, UpgradeInformationGatherer)

    def test_not_yet_installed_upgrades_are_marked_as_proposed(self):
        self.package.with_profile(Builder('genericsetup profile')
                                  .with_upgrade(Builder('plone upgrade step')
                                                .upgrading('1000', to='1001'))
                                  .with_upgrade(Builder('plone upgrade step')
                                                .upgrading('1001', to='1002')))

        with self.package_created():
            self.install_profile('the.package:default', '1001')
            self.assert_gathered_upgrades({
                    'the.package:default': {'proposed': ['1002'],
                                            'done': ['1001']}})

    def test_filtering_proposed_upgrades(self):
        self.package.with_profile(Builder('genericsetup profile')
                                  .with_upgrade(Builder('plone upgrade step')
                                                .upgrading('1000', to='1001'))
                                  .with_upgrade(Builder('plone upgrade step')
                                                .upgrading('1001', to='1002')))

        with self.package_created():
            self.install_profile('the.package:default', '1001')
            self.assert_gathered_upgrades(
                {'the.package:default': {'proposed': ['1002'],
                                         'done': []}},
                proposed_only=True)

    def test_profile_with_outdated_fs_version_is_flagged(self):
        self.package.with_profile(Builder('genericsetup profile')
                                  .named('outdated')
                                  .with_upgrade(Builder('plone upgrade step')
                                                .upgrading('1111', '2222'))
                                  .with_fs_version('2222')
                                  .with_upgrade(Builder('plone upgrade step')
                                                .upgrading('2222', '3333')))

        self.package.with_profile(Builder('genericsetup profile')
                                  .named('correct')
                                  .with_upgrade(Builder('plone upgrade step')
                                                .upgrading('1111', '2222'))
                                  .with_upgrade(Builder('plone upgrade step')
                                                .upgrading('2222', '3333'))
                                  .with_fs_version('3333'))

        with self.package_created():
            self.install_profile('the.package:outdated', '2222')
            self.install_profile('the.package:correct', '2222')
            self.assert_outdated_profiles(['the.package:outdated'],
                                          ignore=[u'plone.app.jquerytools:default',
                                                  u'plone.app.jquery:default'])
            self.assert_gathered_upgrades({
                    'the.package:outdated': {'proposed': ['3333'],
                                            'done': ['2222'],
                                            'outdated_fs_version': ['3333']},
                    'the.package:correct': {'proposed': ['3333'],
                                            'done': ['2222'],
                                            'outdated_fs_version': []}})

    def test_profile_with_no_upgrades_is_not_listed(self):
        self.package.with_profile(Builder('genericsetup profile')
                                  .named('without_upgrades')
                                  .with_fs_version('1'))
        self.package.with_profile(Builder('genericsetup profile')
                                  .named('with_upgrades')
                                  .with_fs_version('2')
                                  .with_upgrade(Builder('plone upgrade step')
                                                .upgrading('1', to='2')))

        with self.package_created():
            self.install_profile('the.package:without_upgrades')
            self.install_profile('the.package:with_upgrades')
            self.assertIn('the.package:with_upgrades', self.get_listed_profiles(),
                          'Profiles with upgrades should be listed.')
            self.assertNotIn('the.package:without_upgrades', self.get_listed_profiles(),
                          'Profiles without upgrades should not be listed.')

    def test_profile_only_listed_when_installed(self):
        self.package.with_profile(Builder('genericsetup profile')
                                  .with_upgrade(Builder('plone upgrade step')
                                                .upgrading('1', to='2')))
        self.package.with_profile(Builder('genericsetup profile')
                                  .named('uninstall'))

        with self.package_created():
            self.assertNotIn('the.package:default', self.get_listed_profiles(),
                             'Not yet installed profiles should not be listed.')

            self.install_profile('the.package:default')
            self.assertIn('the.package:default', self.get_listed_profiles(),
                          'Installed profiles should be listed.')

            if getFSVersionTuple() > (5, 1):
                installer = getMultiAdapter(
                    (self.portal, self.layer['request']), name='installer')
                installer.uninstall_product('the.package')
            else:
                self.portal_quickinstaller.uninstallProducts(['the.package'])
            self.assertNotIn('the.package:default', self.get_listed_profiles(),
                             'Packages uninstalled by quickinstaller should not be listed.')

    def test_plone_profile_is_removed(self):
        self.assertNotIn('Products.CMFPlone:plone',
                         self.get_listed_profiles(filter_package=None),
                         'Products.CMFPlone should never be listed.')

    def test_profiles_are_ordered_by_dependencies(self):
        self.package.with_profile(Builder('genericsetup profile')
                                  .named('one')
                                  .with_dependencies('the.package:two',
                                                     'the.package:four')
                                  .with_upgrade(self.default_upgrade()))

        self.package.with_profile(Builder('genericsetup profile')
                                  .named('two')
                                  .with_dependencies('the.package:three')
                                  .with_upgrade(self.default_upgrade()))

        self.package.with_profile(Builder('genericsetup profile')
                                  .named('three')
                                  .with_dependencies('the.package:four'))

        self.package.with_profile(Builder('genericsetup profile')
                                  .named('four')
                                  .with_upgrade(self.default_upgrade()))

        with self.package_created():
            self.install_profile('the.package:one')
            self.install_profile('the.package:two')
            self.install_profile('the.package:three')
            self.install_profile('the.package:four')

            self.assertEqual(
                ['the.package:four',
                 'the.package:two',
                 'the.package:one'],
                self.get_listed_profiles())

    def test_cyclic_dependencies_raises_an_exception(self):
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

            gatherer = queryAdapter(self.portal_setup, IUpgradeInformationGatherer)
            with self.assertRaises(CyclicDependencies) as cm:
                gatherer.get_profiles()

            self.assertIn(('the.package:bar', 'the.package:foo'),
                          cm.exception.dependencies)

    def test_no_longer_existing_profiles_are_silently_removed(self):
        self.package.with_profile(Builder('genericsetup profile')
                                  .with_upgrade(self.default_upgrade())
                                  .with_dependencies('the.package:removed'))

        self.package.with_profile(Builder('genericsetup profile')
                                  .named('removed')
                                  .with_upgrade(self.default_upgrade()))

        with self.package_created():
            self.install_profile('the.package:default')
            self.assertEqual(['the.package:removed', 'the.package:default'],
                             self.get_listed_profiles())

            from Products.GenericSetup import profile_registry
            profile_registry.unregisterProfile('removed', 'the.package')

            self.assertEqual(['the.package:default'],
                             self.get_listed_profiles())

    def test_not_installable_products_are_not_checked_if_uninstalled(self):
        # Some profiles are not associated with a product.
        # Since we want those profiles to appear in manage-upgrades, we dont verify in the
        # quickinstaller that the product is installed, since it is always not installed because
        # there is no known product.
        # - Products.CMFEditions:CMFEditions
        # - Products.TinyMCE:TinyMCE
        # - plone.app.discussion:default
        # - plone.formwidget.autocomplete:default (depends on Plone version)

        profiles = self.get_listed_profiles(filter_package=None)
        if getFSVersionTuple() < (5,):
            self.assertIn('Products.CMFEditions:CMFEditions', profiles)
            self.assertIn('Products.TinyMCE:TinyMCE', profiles)
        self.assertIn('plone.app.discussion:default', profiles)

    def test_profile_infos(self):
        self.package.with_profile(Builder('genericsetup profile')
                                  .with_upgrade(self.default_upgrade()))

        with self.package_created():
            self.install_profile('the.package:default', version='1000')

            self.assertDictContainsSubset(
                {'product': 'the.package',
                 'id': u'the.package:default',
                 'db_version': u'1000',
                 'version': u'1001',
                 'outdated_fs_version': False,
                 'title': u'the.package',
                 'description': u'',
                 'type': 2,
                 },

                self.get_profiles_by_ids()['the.package:default'])

    def test_deferrable_profile_infos(self):
        self.package.with_profile(
            Builder('genericsetup profile')
            .with_upgrade(Builder('ftw upgrade step')
                          .to(datetime(2011, 1, 1))
                          .calling(NotDeferrableUpgrade)))

        with self.package_created():
            self.install_profile('the.package:default', version='1')
            self.clear_recorded_upgrades('the.package:default')

            profiles = self.get_profiles_by_ids()
            profile_info = profiles['the.package:default']
            upgrade_info = profile_info['upgrades'][0]

            self.assertDictContainsSubset(
                {'profile': 'the.package:default',
                 'done': False,
                 'proposed': True,
                 'orphan': False,
                 'deferrable': False,
                 'outdated_fs_version': False,
                 },
                upgrade_info)

    def test_upgrade_infos(self):
        self.package.with_profile(
            Builder('genericsetup profile')
            .with_upgrade(Builder('plone upgrade step')
                          .upgrading('1000', to='1001')
                          .titled(u'Add action')
                          .with_description('Some details...')))

        with self.package_created():
            self.install_profile('the.package:default', version='1000')
            profile_info = self.get_profiles_by_ids()['the.package:default']
            upgrade_info = profile_info['upgrades'][0]

            self.assertDictContainsSubset(
                {'title': u'Add action',
                 'description': u'Some details...',
                 'profile': 'the.package:default',
                 'api_id': '1001@the.package:default',
                 'ssource': '1000',
                 'source': ('1000',),
                 'sdest': '1001',
                 'dest': ('1001',),
                 'done': False,
                 'proposed': True,
                 'orphan': False,
                 'deferrable': False,
                 'outdated_fs_version': False,
                 'haspath': ('1001',)},
                upgrade_info)

    def test_upgrade_infos_proposes_deferrable_by_default(self):
        self.package.with_profile(
            Builder('genericsetup profile')
            .with_upgrade(Builder('ftw upgrade step')
                          .to(datetime(2011, 1, 1))
                          .as_deferrable()))

        with self.package_created():
            self.install_profile('the.package:default', version='1')
            self.clear_recorded_upgrades('the.package:default')
            self.assert_gathered_upgrades({
                    'the.package:default': {
                        'done': [],
                        'proposed': ['20110101000000'],
                        'orphan': []}})

            profiles = self.get_profiles_by_ids()
            profile_info = profiles['the.package:default']
            upgrade_info = profile_info['upgrades'][0]

            self.assertDictContainsSubset(
                {'profile': 'the.package:default',
                 'done': False,
                 'proposed': True,
                 'orphan': False,
                 'deferrable': True,
                 'outdated_fs_version': False,
                 },
                upgrade_info)

    def test_deferrable_upgrades_are_proposed_when_specified(self):
        self.package.with_profile(
            Builder('genericsetup profile')
            .with_upgrade(Builder('ftw upgrade step')
                          .to(datetime(2011, 1, 1))
                          .as_deferrable()))

        with self.package_created():
            self.install_profile('the.package:default', version='1')
            self.clear_recorded_upgrades('the.package:default')
            self.assert_gathered_upgrades({
                    'the.package:default': {
                        'done': [],
                        'proposed': ['20110101000000'],
                        'orphan': []}},
                    propose_deferrable=True)

            profiles = self.get_profiles_by_ids(propose_deferrable=True)
            profile_info = profiles['the.package:default']
            upgrade_info = profile_info['upgrades'][0]

            self.assertDictContainsSubset(
                {'profile': 'the.package:default',
                 'done': False,
                 'proposed': True,
                 'orphan': False,
                 'deferrable': True,
                 'outdated_fs_version': False,
                 },
                upgrade_info)

    def test_orphane_upgrades_are_marked(self):
        self.package.with_profile(
            Builder('genericsetup profile')
            .with_upgrade(Builder('plone upgrade step').upgrading('1000', to='1001'))
            .with_upgrade(Builder('ftw upgrade step').to(datetime(2011, 1, 1)))
            .with_upgrade(Builder('ftw upgrade step').to(datetime(2012, 1, 1)))
            .with_upgrade(Builder('ftw upgrade step').to(datetime(2013, 1, 1))))

        with self.package_created():
            self.install_profile('the.package:default', version='20120101000000')
            self.record_installed_upgrades('the.package:default', '20120101000000')
            self.assert_gathered_upgrades({
                    'the.package:default': {
                        'done': ['1001', '20120101000000'],
                        'proposed': ['20110101000000', '20130101000000'],
                        'orphan': ['20110101000000']}})

    def test_do_not_propose_future_upgrades_marked_as_executed(self):
        """When the installed version is older than an upgrade step, but the upgrade
        step was already marked as executed, the upgrade step should not be proposed.

        This is mainly useful for when the IUpgradeStepRecorder is extend with additional
        logic.
        """
        self.package.with_profile(
            Builder('genericsetup profile')
            .with_upgrade(Builder('plone upgrade step').upgrading('1000', to='1001'))
            .with_upgrade(Builder('ftw upgrade step').to(datetime(2011, 1, 1)))
            .with_upgrade(Builder('ftw upgrade step').to(datetime(2012, 1, 1)))
            .with_upgrade(Builder('ftw upgrade step').to(datetime(2013, 1, 1))))

        with self.package_created():
            self.install_profile('the.package:default', version='20110101000000')
            self.record_installed_upgrades(
                'the.package:default', '20110101000000', '20130101000000')
            self.assert_gathered_upgrades({
                    'the.package:default': {
                        'done': ['1001', '20110101000000', '20130101000000'],
                        'proposed': ['20120101000000'],
                        'orphan': []}})

    def test_human_readable_timestamp_versions_are_added_to_profiles(self):
        self.package.with_profile(
            Builder('genericsetup profile')
            .with_upgrade(Builder('ftw upgrade step')
                          .to(datetime(2011, 12, 30, 17, 45, 59))))

        with self.package_created():
            self.install_profile('the.package:default')

            self.assertDictContainsSubset(
                {'id': u'the.package:default',
                 'db_version': u'20111230174559',
                 'formatted_db_version': u'2011/12/30 17:45',
                 'version': u'20111230174559',
                 'formatted_version': u'2011/12/30 17:45'},
                self.get_profiles_by_ids()['the.package:default'])

    def test_human_readable_timestamp_versions_are_added_to_upgrades(self):
        self.package.with_profile(
            Builder('genericsetup profile')
            .with_upgrade(Builder('ftw upgrade step').to('20141117093040'))
            .with_upgrade(Builder('ftw upgrade step').to('20141230104550')))

        with self.package_created():
            self.install_profile('the.package:default')
            profile_info = self.get_profiles_by_ids()['the.package:default']
            upgrade_info = profile_info['upgrades'][1]

            self.assertDictContainsSubset(
                {'ssource': '20141117093040',
                 'fsource': '2014/11/17 09:30',
                 'sdest': '20141230104550',
                 'fdest': '2014/12/30 10:45'},
                upgrade_info)

    def test_get_upgrades_by_api_ids(self):
        self.package.with_profile(
            Builder('genericsetup profile')
            .with_upgrade(Builder('ftw upgrade step').to(datetime(2011, 1, 1))))

        with self.package_created():
            self.install_profile('the.package:default')

            gatherer = queryAdapter(self.portal_setup, IUpgradeInformationGatherer)
            upgrade_info, = gatherer.get_upgrades_by_api_ids(
                '20110101000000@the.package:default')
            self.assertDictContainsSubset(
                {'api_id': u'20110101000000@the.package:default',
                 'sdest': u'20110101000000'},
                upgrade_info)

    def test_get_upgrades_by_api_ids_orders_upgrades(self):
        self.package.with_profile(
            Builder('genericsetup profile')
            .with_upgrade(Builder('ftw upgrade step').to(datetime(2011, 1, 1)))
            .with_upgrade(Builder('ftw upgrade step').to(datetime(2012, 2, 2))))

        with self.package_created():
            self.install_profile('the.package:default')

            gatherer = queryAdapter(self.portal_setup, IUpgradeInformationGatherer)
            self.assertEqual(
                gatherer.get_upgrades_by_api_ids('20110101000000@the.package:default',
                                                 '20120202000000@the.package:default'),
                gatherer.get_upgrades_by_api_ids('20120202000000@the.package:default',
                                                 '20110101000000@the.package:default'))

    def test_get_upgrades_by_api_ids_raises_upgrade_not_found(self):
        gatherer = queryAdapter(self.portal_setup, IUpgradeInformationGatherer)
        with self.assertRaises(UpgradeNotFound) as cm:
            gatherer.get_upgrades_by_api_ids('foo@bar:default')
        self.assertEqual('foo@bar:default', cm.exception.api_id)
        self.assertEqual('The upgrade "foo@bar:default" could not be found.',
                         str(cm.exception))

    def get_listed_profiles(self, filter_package='the.package'):
        gatherer = queryAdapter(self.portal_setup, IUpgradeInformationGatherer)
        result = gatherer.get_profiles()
        profiles = [profile['id'] for profile in result]
        if filter_package:
            profiles = [
                profile for profile in profiles
                if profile.startswith(filter_package)
            ]
        return profiles

    def get_profiles_by_ids(self, **kwargs):
        gatherer = queryAdapter(self.portal_setup, IUpgradeInformationGatherer)
        result = gatherer.get_profiles(**kwargs)
        return dict([(profile['id'], profile) for profile in result])

    def assert_outdated_profiles(self, expected_profiles, ignore=()):
        gatherer = queryAdapter(self.portal_setup, IUpgradeInformationGatherer)
        result = gatherer.get_profiles()
        got_profiles = [profile['id'] for profile in result
                        if profile['outdated_fs_version'] and profile['id'] not in ignore]
        self.assertEqual(expected_profiles, got_profiles,
                         'Unexpected outdated fs versions for profiles.')


class TestExtendAutoUpgradesWithHumanFormattedDateVersion(TestCase):

    def test_formats_timestamp_source_versions(self):
        input = {'ssource': '20141214183059',
                 'sdest': '1'}
        expected = {'ssource': '20141214183059',
                    'fsource': '2014/12/14 18:30',
                    'sdest': '1'}
        self.assertDictEqual(expected, self.format_upgrade_step(input))

    def test_formats_timestamp_dest_versions(self):
        input = {'ssource': '1',
                 'sdest': '20141214183059'}
        expected = {'ssource': '1',
                    'sdest': '20141214183059',
                    'fdest': '2014/12/14 18:30'}
        self.assertDictEqual(expected, self.format_upgrade_step(input))

    def test_does_not_format_non_timestamp_versions(self):
        input = {'ssource': '1',
                 'sdest': '2'}
        expected = {'ssource': '1',
                    'sdest': '2'}
        self.assertDictEqual(expected, self.format_upgrade_step(input))

    def test_does_not_fail_on_non_timestamp_versions_looking_like_timestamps(self):
        input = {'ssource': '10000000000000',
                 'sdest': '1'}
        expected = {'ssource': '10000000000000',
                    'sdest': '1'}
        self.assertDictEqual(expected, self.format_upgrade_step(input))

        input = {'ssource': '1',
                 'sdest': '10000000000000'}
        expected = {'ssource': '1',
                    'sdest': '10000000000000'}
        self.assertDictEqual(expected, self.format_upgrade_step(input))

    def format_upgrade_step(self, upgrade_step):
        profiles = [{'upgrades': [upgrade_step]}]
        output = extend_auto_upgrades_with_human_formatted_date_version(profiles)
        return output[0]['upgrades'][0]
