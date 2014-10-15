from ftw.upgrade.interfaces import IExecutioner
from ftw.upgrade.testing import FTW_UPGRADE_FIXTURE
from plone.app.testing import applyProfile
from plone.app.testing import IntegrationTesting
from plone.app.testing import PloneSandboxLayer
from Products.CMFCore.utils import getToolByName
from unittest2 import TestCase
from zope.component import getAdapter
from zope.configuration import xmlconfig


PROFILE_NAME = 'ftw.upgrade.tests.directory_upgrades:default'


class DirectoryUpgradesLayer(PloneSandboxLayer):

    defaultBases = (FTW_UPGRADE_FIXTURE,)

    def setUpZope(self, app, configurationContext):
        import ftw.upgrade.tests.directory_upgrades
        xmlconfig.file('configure.zcml',
                       ftw.upgrade.tests.directory_upgrades,
                       context=configurationContext)


DIRECTORY_UPGRADES_FIXTURE = DirectoryUpgradesLayer()
DIRECTORY_UPGRADES_INTEGRATION = IntegrationTesting(
    bases=(DIRECTORY_UPGRADES_FIXTURE,),
    name='directory-upgrades:integration')


class TestDirectoryUpgradeSteps(TestCase):
    layer = DIRECTORY_UPGRADES_INTEGRATION

    def setUp(self):
        self.portal = self.layer['portal']
        self.portal_setup = getToolByName(self.portal, 'portal_setup')
        self.portal_actions = getToolByName(self.portal, 'portal_actions')

    def test_installing_profile_sets_version_to_latest_upgrade(self):
        applyProfile(self.layer['portal'], PROFILE_NAME)
        version = self.portal_setup.getLastVersionForProfile(PROFILE_NAME)
        self.assertEqual(('20140101083000',), version)

    def test_migrating_profile_with_upgrade_steps(self):
        self.portal_setup.setLastVersionForProfile(PROFILE_NAME, u'1')
        executioner = IExecutioner(self.portal_setup)
        first_upgrade, = self.portal_setup.listUpgrades(PROFILE_NAME)

        self.assertIsNone(self.get_action())
        executioner.install([(PROFILE_NAME, [first_upgrade['id']])])
        self.assertEqual('The Test Action', self.get_action().title)

    def get_action(self):
        return self.portal_actions.portal_tabs.get('test-action')
