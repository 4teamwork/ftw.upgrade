from ftw.builder import Builder
from ftw.builder.utils import serialize_callable
from ftw.upgrade import UpgradeStep
from ftw.upgrade.tests.base import UpgradeTestCase
from Products.CMFCore.utils import getToolByName


class TestImportProfileUpgradeStepDirective(UpgradeTestCase):

    def setUp(self):
        super(TestImportProfileUpgradeStepDirective, self).setUp()
        self.portal_actions = getToolByName(self.portal, 'portal_actions')

    def test_upgrade_step_directive_without_handler(self):
        self.package.with_profile(Builder('genericsetup profile').with_fs_version('2'))
        self.package.with_zcml_include('ftw.upgrade', file='meta.zcml')
        self.package.with_zcml_node('upgrade-step:importProfile',
                                    title='Add test action.',
                                    profile='the.package:default',
                                    source='1',
                                    destination='2',
                                    directory='upgrade-profile/2')
        self.package.with_file('upgrade-profile/2/actions.xml',
                               self.asset('test-action.xml'), makedirs=True)

        with self.package_created():
            self.install_profile('the.package:default', '1')
            self.assertIsNone(self.get_action())
            self.install_profile_upgrades('the.package:default')
            self.assertEqual('The Test Action', self.get_action().title)

    def test_upgrade_step_directive_with_handler(self):
        class Upgrade(UpgradeStep):
            def __call__(self):
                self.install_upgrade_profile()
                portal_actions = self.getToolByName('portal_actions')
                action = portal_actions.portal_tabs.get('test-action')
                assert action, 'The "test-action" was not created on import.'
                action.title = 'Title was changed.'

        self.package.with_profile(Builder('genericsetup profile').with_fs_version('2'))
        self.package.with_zcml_include('ftw.upgrade', file='meta.zcml')
        self.package.with_zcml_node('upgrade-step:importProfile',
                                    title='Add and rename test action.',
                                    profile='the.package:default',
                                    source='1',
                                    destination='2',
                                    directory='upgrade-profile/1',
                                    handler='.to2.Upgrade')
        self.package.with_file('to2.py', serialize_callable(Upgrade))
        self.package.with_file('upgrade-profile/1/actions.xml',
                               self.asset('test-action.xml'), makedirs=True)

        with self.package_created():
            self.install_profile('the.package:default', '1')
            self.assertIsNone(self.get_action())
            self.install_profile_upgrades('the.package:default')
            self.assertEqual('Title was changed.', self.get_action().title)

    def get_action(self):
        return self.portal_actions.portal_tabs.get('test-action')
