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
