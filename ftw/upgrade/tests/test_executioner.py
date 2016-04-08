from ftw.builder import Builder
from ftw.upgrade.executioner import Executioner
from ftw.upgrade.interfaces import IExecutioner
from ftw.upgrade.tests.base import UpgradeTestCase
from Products.CMFCore.utils import getToolByName
from zope.component import queryAdapter
from zope.interface.verify import verifyClass
import transaction


class TestExecutioner(UpgradeTestCase):

    def test_component_is_registered(self):
        setup_tool = getToolByName(self.layer['portal'], 'portal_setup')
        executioner = queryAdapter(setup_tool, IExecutioner)
        self.assertNotEqual(None, executioner)

    def test_implements_interface(self):
        verifyClass(IExecutioner, Executioner)

    def test_installs_upgrades(self):
        def upgrade(setup_context):
            portal = setup_context.portal_url.getPortalObject()
            portal.upgrade_step_executed = True

        self.package.with_profile(Builder('genericsetup profile')
                                   .with_upgrade(Builder('plone upgrade step')
                                                 .upgrading('1000', to='1002')
                                                 .calling(upgrade)))

        self.portal.upgrade_step_executed = False
        with self.package_created():
            self.install_profile('the.package:default', version='1000')
            self.assertFalse(self.portal.upgrade_step_executed)
            self.install_profile_upgrades('the.package:default')
            self.assertTrue(self.portal.upgrade_step_executed)

    def test_install_upgrades_by_api_ids(self):
        def upgrade(setup_context):
            portal = setup_context.portal_url.getPortalObject()
            portal.upgrade_step_executed = True

        self.package.with_profile(Builder('genericsetup profile')
                                   .with_upgrade(Builder('plone upgrade step')
                                                 .upgrading('1000', to='1002')
                                                 .calling(upgrade)))

        self.portal.upgrade_step_executed = False
        with self.package_created():
            self.install_profile('the.package:default', version='1000')
            self.assertFalse(self.portal.upgrade_step_executed)
            executioner = queryAdapter(self.portal_setup, IExecutioner)
            executioner.install_upgrades_by_api_ids('1002@the.package:default')
            self.assertTrue(self.portal.upgrade_step_executed)

    def test_transaction_note(self):
        self.package.with_profile(
            Builder('genericsetup profile')
            .with_upgrade(Builder('plone upgrade step')
                          .upgrading('1000', to='1001')
                          .titled('Register "foo" utility'))
            .with_upgrade(Builder('plone upgrade step')
                          .upgrading('1001', to='1002')
                          .titled('Update email address'))
            .with_upgrade(Builder('plone upgrade step')
                          .upgrading('1002', to='1003')
                          .titled('Update email from name')))

        with self.package_created():
            self.install_profile('the.package:default', version='1000')
            self.install_profile_upgrades('the.package:default')
            self.assertMultiLineEqual(
                u'the.package:default -> 1001 (Register "foo" utility)\n'
                u'the.package:default -> 1002 (Update email address)\n'
                u'the.package:default -> 1003 (Update email from name)',
                transaction.get().description)

    def test_after_commit_hook(self):
        self.package.with_profile(
            Builder('genericsetup profile')
            .with_upgrade(Builder('plone upgrade step')
                          .upgrading('1000', to='1001')
                          .titled('Register "foo" utility')))

        with self.package_created():
            self.install_profile('the.package:default', version='1000')
            self.install_profile_upgrades('the.package:default')

            hooks = list(transaction.get().getAfterCommitHooks())
            hook_funcs = [h[0] for h in hooks]

            self.assertIn(
                'notification_hook',
                [f.func_name for f in hook_funcs],
                'Our notification_hook should be registered')

            transaction.commit()
            self.assertEquals(
                [],
                list(transaction.get().getAfterCommitHooks()),
                'Hook registrations should not persist across transactions')

    def test_resources_are_recooked_after_installing_upgrades(self):
        self.package.with_profile(
            Builder('genericsetup profile')
            .with_upgrade(Builder('plone upgrade step').upgrading('1000', to='1001')))
        with self.package_created():
            self.install_profile('the.package:default', version='1000')
            with self.assert_resources_recooked():
                self.install_profile_upgrades('the.package:default')

    def test_updates_quickinstaller_version(self):
        quickinstaller = getToolByName(self.portal, 'portal_quickinstaller')

        self.package.with_profile(Builder('genericsetup profile')
                                  .with_upgrade(Builder('plone upgrade step')
                                                .upgrading('1000', to='1001')))
        self.package.with_version('1.1')

        with self.package_created():
            self.install_profile('the.package:default', version='1000')
            quickinstaller.get('the.package').installedversion = '1.0'
            self.assertEquals('1.0', quickinstaller.get('the.package').getInstalledVersion())
            self.install_profile_upgrades('the.package:default')
            self.assertEquals('1.1', quickinstaller.get('the.package').getInstalledVersion())

    def test_install_profiles_by_profile_ids(self):
        self.package.with_profile(Builder('genericsetup profile')
                                  .with_upgrade(Builder('plone upgrade step')
                                                .upgrading('1000', to='1001')))

        self.setup_logging()
        profile_id = 'the.package:default'
        with self.package_created():
            executioner = queryAdapter(self.portal_setup, IExecutioner)
            executioner.install_profiles_by_profile_ids(profile_id)
            self.assertEquals(
                ['Installing profile the.package:default.',
                 'Done installing profile the.package:default.'],
                self.get_log())

            self.purge_log()
            executioner.install_profiles_by_profile_ids(profile_id)
            self.assertEquals(
                ['Ignoring already installed profile the.package:default.'],
                self.get_log())

            self.purge_log()
            executioner.install_profiles_by_profile_ids(profile_id,
                                                        force_reinstall=True)
            self.assertEquals(
                ['Installing profile the.package:default.',
                 'Done installing profile the.package:default.'],
                self.get_log())
