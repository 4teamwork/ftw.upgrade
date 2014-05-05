from Products.CMFCore.utils import getToolByName
from ftw.upgrade.executioner import Executioner
from ftw.upgrade.interfaces import IExecutioner
from ftw.upgrade.testing import FTW_UPGRADE_FIXTURE
from ftw.upgrade.tests.upgrades.foo import IFoo
from plone.app.testing import FunctionalTesting
from plone.app.testing import PloneSandboxLayer
from unittest2 import TestCase
from zope.component import queryAdapter
from zope.component import queryUtility
from zope.configuration import xmlconfig
from zope.interface.verify import verifyClass
import transaction


class UpgradesRegistered(PloneSandboxLayer):

    defaultBases = (FTW_UPGRADE_FIXTURE,)

    def setUpZope(self, app, configurationContext):
        import ftw.upgrade.tests.upgrades
        xmlconfig.file('foo.zcml', ftw.upgrade.tests.upgrades,
                       context=configurationContext)
        xmlconfig.file('bar.zcml', ftw.upgrade.tests.upgrades,
                       context=configurationContext)


UPGRADES_REGISTERED = UpgradesRegistered()
UPGRADES_REGISTERED_FUNCTIONAL = FunctionalTesting(
    bases=(UPGRADES_REGISTERED,), name='FtwUpgrade.exec.foo:Functional')


class TestExecutioner(TestCase):

    layer = UPGRADES_REGISTERED_FUNCTIONAL

    def test_component_is_registered(self):
        setup_tool = getToolByName(self.layer['portal'], 'portal_setup')
        executioner = queryAdapter(setup_tool, IExecutioner)
        self.assertNotEqual(None, executioner)

    def test_implements_interface(self):
        verifyClass(IExecutioner, Executioner)

    def test_installs_upgrades(self):
        profileid = 'ftw.upgrade.tests.profiles:foo'
        setup_tool = getToolByName(self.layer['portal'], 'portal_setup')

        self.assertEqual(None, queryUtility(IFoo))
        self.assertEqual('unknown',
                         setup_tool.getLastVersionForProfile(profileid))

        self.install_profile_upgrades(profileid)
        self.assertNotEqual(None, queryUtility(IFoo))
        self.assertEqual(('2',),
                         setup_tool.getLastVersionForProfile(profileid))

    def test_transaction_note(self):
        self.install_profile_upgrades('ftw.upgrade.tests.profiles:foo')
        self.install_profile_upgrades('ftw.upgrade.tests.profiles:bar')
        self.assertEquals(
            u'ftw.upgrade.tests.profiles:foo -> 2 (Registers foo utility)\n'
            u'ftw.upgrade.tests.profiles:bar -> 2 (Update email address)',
            transaction.get().description)

    def install_profile_upgrades(self, profileid):
        setup_tool = getToolByName(self.layer['portal'], 'portal_setup')
        executioner = queryAdapter(setup_tool, IExecutioner)
        upgrade_ids = [upgrade['id'] for upgrade
                       in setup_tool.listUpgrades(profileid)]
        executioner.install([(profileid, upgrade_ids)])
