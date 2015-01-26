from datetime import datetime
from ftw.builder import Builder
from ftw.builder import create
from ftw.upgrade.tests.base import CommandAndInstanceTestCase
from ftw.upgrade.tests.helpers import no_logging_threads
from persistent.list import PersistentList
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
import os
import transaction


class TestInstallCommand(CommandAndInstanceTestCase):

    def setUp(self):
        super(TestInstallCommand, self).setUp()
        self.write_zconf_with_test_instance()

    def test_help(self):
        self.upgrade_script('install --help')

    def test_install_proposed_upgrades(self):
        self.package.with_profile(
            Builder('genericsetup profile')
            .with_upgrade(Builder('ftw upgrade step').to(datetime(2011, 1, 1))
                          .named('The upgrade')))

        with self.package_created():
            self.install_profile('the.package:default', version='1')
            self.clear_recorded_upgrades('the.package:default')

            self.assertFalse(self.is_installed('the.package:default', datetime(2011, 1, 1)))
            exitcode, output = self.upgrade_script('install -s plone --proposed')
            self.assertEquals(0, exitcode)
            transaction.begin()  # sync transaction
            self.assertTrue(self.is_installed('the.package:default', datetime(2011, 1, 1)))
            self.assertIn('Result: SUCCESS', output)

    def test_install_failure_raises_exitcode(self):
        def failing_upgrade(setup_context):
            raise KeyError('foo')

        self.package.with_profile(
            Builder('genericsetup profile')
            .with_upgrade(Builder('plone upgrade step')
                          .upgrading('1', to='2')
                          .calling(failing_upgrade)))

        with self.package_created():
            self.install_profile('the.package:default', version='1')
            with no_logging_threads():
                exitcode, output = self.upgrade_script('install -s plone --proposed',
                                                       assert_exitcode=False)
            self.assertEquals(3, exitcode)
            self.assertIn('Result: FAILURE', output)

    def test_install_list_of_upgrades(self):
        self.package.with_profile(
            Builder('genericsetup profile')
            .with_upgrade(Builder('ftw upgrade step').to(datetime(2011, 1, 1))
                          .named('The upgrade')))

        with self.package_created():
            self.install_profile('the.package:default', version='1')
            self.clear_recorded_upgrades('the.package:default')

            self.assertFalse(self.is_installed('the.package:default', datetime(2011, 1, 1)))
            exitcode, output = self.upgrade_script(
                'install -s plone --upgrades 20110101000000@the.package:default')
            self.assertEquals(0, exitcode)
            transaction.begin()  # sync transaction
            self.assertTrue(self.is_installed('the.package:default', datetime(2011, 1, 1)))
            self.assertIn('Result: SUCCESS', output)

    def test_virtual_host_monster_is_configured_by_environment_variable(self):
        os.environ['UPGRADE_PUBLIC_URL'] = 'https://foo.bar.com/baz'
        self.layer['portal'].upgrade_info = PersistentList()

        setRoles(self.layer['portal'], TEST_USER_ID, ['Manager'])
        create(Builder('folder').with_id('the-folder'))

        def upgrade_step(setup_context):
            portal = setup_context.portal_url.getPortalObject()
            folder = portal.get('the-folder')
            portal.upgrade_info.append(folder.absolute_url())

        self.package.with_profile(
            Builder('genericsetup profile')
            .with_upgrade(Builder('plone upgrade step').upgrading('1', to='2')
                          .calling(upgrade_step)))

        with self.package_created():
            self.install_profile('the.package:default', version='1')
            exitcode, output = self.upgrade_script('install -s plone --proposed')
            self.assertEquals(0, exitcode)
            transaction.begin()  # sync transaction
            self.assertEquals(['https://foo.bar.com/baz/the-folder'],
                              self.layer['portal'].upgrade_info)
