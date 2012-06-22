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


class UpgradesRegistered(PloneSandboxLayer):

    defaultBases = (FTW_UPGRADE_FIXTURE,)

    def setUpZope(self, app, configurationContext):
        import ftw.upgrade.tests.upgrades
        xmlconfig.file('foo.zcml', ftw.upgrade.tests.upgrades,
                       context=configurationContext)


UPGRADES_REGISTERED = UpgradesRegistered()
UPGRADES_REGISTERED_FUNCTIONAL = FunctionalTesting(
    bases=(UPGRADES_REGISTERED,), name='FtwUpgrade.exec.foo:Functional')


class TestExecutioner(TestCase):

    layer = UPGRADES_REGISTERED_FUNCTIONAL

    def test_component_is_registered(self):
        setup_tool = getToolByName(self.layer['portal'], 'portal_setup')
        executioner = queryAdapter(setup_tool, IExecutioner)
        self.assertNotEqual(executioner, None)

    def test_implements_interface(self):
        verifyClass(IExecutioner, Executioner)

    def test_installs_upgrades(self):
        profileid = 'ftw.upgrade.tests:foo'
        setup_tool = getToolByName(self.layer['portal'], 'portal_setup')

        self.assertEqual(queryUtility(IFoo), None)
        self.assertEqual(
            setup_tool.getLastVersionForProfile(profileid), 'unknown')

        upgrades = setup_tool.listUpgrades('ftw.upgrade.tests:foo')
        self.assertEqual(len(upgrades), 1)
        id_ = upgrades[0]['id']

        executioner = queryAdapter(setup_tool, IExecutioner)
        executioner.install([(profileid, [id_])])

        self.assertNotEqual(queryUtility(IFoo), None)
        self.assertEqual(
            setup_tool.getLastVersionForProfile(profileid), ('2',))
