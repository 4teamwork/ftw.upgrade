from Products.CMFCore.utils import getToolByName
from ftw.upgrade.interfaces import IExecutioner
from ftw.upgrade.interfaces import IUpgradeInformationGatherer
from ftw.upgrade.testing import FTW_UPGRADE_FIXTURE
from plone.app.testing import FunctionalTesting
from plone.app.testing import PloneSandboxLayer
from plone.app.testing import applyProfile
from unittest2 import TestCase
from zope.component import queryAdapter
from zope.configuration import xmlconfig


BAR_PROFILE = 'ftw.upgrade.tests.profiles:bar'


class BarUpgrades(PloneSandboxLayer):

    defaultBases = (FTW_UPGRADE_FIXTURE,)

    def setUpZope(self, app, configurationContext):
        import ftw.upgrade.tests.profiles
        xmlconfig.file('configure.zcml', ftw.upgrade.tests.profiles,
                       context=configurationContext)
        import ftw.upgrade.tests.upgrades
        xmlconfig.file('bar.zcml', ftw.upgrade.tests.upgrades,
                       context=configurationContext)

    def setUpPloneSite(self, portal):
        applyProfile(portal, BAR_PROFILE)


BAR_UPGRADES_FIXTURE = BarUpgrades()
BAR_UPGRADES_FUNCTIONAL = FunctionalTesting(
    bases=(BAR_UPGRADES_FIXTURE,), name='FtwUpgrade.exec.bar:Functional')


class TestImportProfileUpgradeStepDirective(TestCase):

    layer = BAR_UPGRADES_FUNCTIONAL

    def setUp(self):
        self.portal = self.layer['portal']
        setup_tool = getToolByName(self.portal, 'portal_setup')
        self.gatherer = queryAdapter(setup_tool, IUpgradeInformationGatherer)
        self.executioner = queryAdapter(setup_tool, IExecutioner)

    def test_profile_upgrade_step_changes_site_email(self):
        # The example upgrade step changes the sites email address.
        portal = self.layer['portal']
        self.assertEqual('', portal.getProperty('email_from_address'))
        self.executioner.install([(BAR_PROFILE, self.get_bar_upgrade_ids())])
        self.assertEqual('foo@bar.com', portal.getProperty('email_from_address'))

    def get_bar_upgrade_ids(self):
        bar_profile = filter(lambda prof: prof.get('id') == BAR_PROFILE,
                             self.gatherer.get_upgrades())[0]
        upgrades = [upgrade.get('id') for upgrade in bar_profile.get('upgrades')]
        return upgrades
