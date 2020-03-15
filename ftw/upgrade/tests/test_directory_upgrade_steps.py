from datetime import datetime
from ftw.builder import Builder
from ftw.upgrade import UpgradeStep
from ftw.upgrade.directory.subscribers import no_upgrade_step_marking
from ftw.upgrade.interfaces import IExecutioner
from ftw.upgrade.interfaces import IUpgradeStepRecorder
from ftw.upgrade.tests.base import UpgradeTestCase
from Products.CMFCore.utils import getToolByName
from zope.component import getMultiAdapter


class TestDirectoryUpgradeSteps(UpgradeTestCase):

    def setUp(self):
        super(TestDirectoryUpgradeSteps, self).setUp()
        self.portal_actions = getToolByName(self.portal, 'portal_actions')

    def test_installing_profile_sets_version_to_latest_upgrade(self):
        self.package.with_profile(Builder('genericsetup profile')
                                  .with_upgrade(Builder('ftw upgrade step')
                                                .to(datetime(2014, 1, 1))))

        with self.package_created():
            self.install_profile('the.package:default')
            version = self.portal_setup.getLastVersionForProfile('the.package:default')
            self.assertEqual(('20140101000000',), version)

    def test_installing_profile_marks_all_upgrade_steps_as_installed_too(self):
        self.package.with_profile(Builder('genericsetup profile')
                                  .with_upgrade(Builder('ftw upgrade step')
                                                .to(datetime(2011, 1, 1))))

        with self.package_created():
            recorder = getMultiAdapter((self.portal, 'the.package:default'),
                                       IUpgradeStepRecorder)
            self.assertFalse(
                recorder.is_installed('20110101000000'),
                'Expected upgrade steps to not be marked as installed'
                ' before importing profile.')

            self.install_profile('the.package:default')

            self.assertTrue(
                recorder.is_installed('20110101000000'),
                'Expected upgrade steps to be marked as installed'
                ' after importing profile.')

    def test_installing_profile_does_not_mark_upgrade_step_as_installed_on_partial_import(self):
        self.package.with_profile(Builder('genericsetup profile')
                                  .with_upgrade(Builder('ftw upgrade step')
                                                .to(datetime(2011, 1, 1))))

        with self.package_created():
            recorder = getMultiAdapter((self.portal, 'the.package:default'),
                                       IUpgradeStepRecorder)
            self.assertFalse(
                recorder.is_installed('20110101000000'),
                'Expected upgrade steps to not be marked as installed'
                ' before importing profile.')

            self.portal_setup.runImportStepFromProfile('profile-the.package:default', 'typeinfo')

            self.assertFalse(
                recorder.is_installed('20110101000000'),
                'Expected upgrade steps to not be marked as installed'
                ' because of a partial import.')

    def test_context_manager_for_disabling_upgrade_step_marking(self):
        self.package.with_profile(Builder('genericsetup profile')
                                  .with_upgrade(Builder('ftw upgrade step')
                                                .to(datetime(2011, 1, 1))))

        with self.package_created():
            recorder = getMultiAdapter((self.portal, 'the.package:default'),
                                       IUpgradeStepRecorder)
            self.assertFalse(
                recorder.is_installed('20110101000000'),
                'Expected upgrade steps to not be marked as installed'
                ' before importing profile.')

            with no_upgrade_step_marking():
                self.install_profile('the.package:default')

            self.assertFalse(
                recorder.is_installed('20110101000000'),
                'Expected upgrade steps to not be marked as installed'
                ' because marking is prevented for all profiles.')

            with no_upgrade_step_marking('the.package:default'):
                self.install_profile('the.package:default')

            self.assertFalse(
                recorder.is_installed('20110101000000'),
                'Expected upgrade steps to not be marked as installed'
                ' because marking is prevented for this profile.')

            with no_upgrade_step_marking('OTHER.package:default'):
                self.install_profile('the.package:default')

            self.assertTrue(
                recorder.is_installed('20110101000000'),
                'Expected upgrade steps to be marked as installed'
                ' because it is only prevented for other profiles.')

    def test_associated_upgrade_step_profile_is_imported(self):
        class AddTestAction(UpgradeStep):
            def __call__(self):
                self.install_upgrade_profile()

        self.package.with_profile(
            Builder('genericsetup profile')
            .with_upgrade(Builder('ftw upgrade step')
                          .to(datetime(2011, 1, 1))
                          .with_file('actions.xml', self.asset('test-action.xml'))
                          .calling(AddTestAction)))

        with self.package_created():
            self.install_profile('the.package:default')
            self.assertIsNone(self.get_action())
            self.install_profile_upgrades('the.package:default')
            self.assertEqual('The Test Action', self.get_action().title)

    def test_running_upgrade_steps_marks_them_as_installed(self):
        self.package.with_profile(Builder('genericsetup profile')
                                  .with_upgrade(Builder('ftw upgrade step')
                                                .to(datetime(2011, 1, 1))))

        with self.package_created():
            recorder = getMultiAdapter((self.portal, 'the.package:default'),
                                       IUpgradeStepRecorder)

            self.portal_setup.setLastVersionForProfile('the.package:default', u'0')
            self.assertFalse(
                recorder.is_installed('20110101000000'),
                'Expected upgrade steps to not be marked as installed'
                ' before importing profile.')

            executioner = IExecutioner(self.portal_setup)
            first_upgrade, = self.portal_setup.listUpgrades('the.package:default')
            executioner.install([('the.package:default', [first_upgrade['id']])])

            self.assertTrue(
                recorder.is_installed('20110101000000'),
                'Expected upgrade steps to be marked as installed'
                ' after upgrading.')

    def test_base_profile_and_target_version_are_provided(self):
        self.portal.upgrade_infos = {}

        class StoreUpgradeInfos(UpgradeStep):
            def __call__(self):
                self.portal.upgrade_infos.update({
                    'base_profile': self.base_profile,
                    'target_version': self.target_version,
                })

        self.package.with_profile(
            Builder('genericsetup profile')
            .with_upgrade(Builder('ftw upgrade step')
                          .to(datetime(2011, 1, 1))
                          .calling(StoreUpgradeInfos)))

        with self.package_created():
            self.install_profile('the.package:default')
            self.assertEqual({}, self.portal.upgrade_infos)
            self.install_profile_upgrades('the.package:default')
            self.assertEqual(
                {'base_profile': u'profile-the.package:default',
                 'target_version': '20110101000000'},
                self.portal.upgrade_infos)

    def get_action(self):
        return self.portal_actions.portal_tabs.get('test-action')
