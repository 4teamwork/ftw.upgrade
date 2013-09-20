from Acquisition import aq_parent
from ftw.upgrade.api.adapters import IUpgradablePloneSite
from ftw.upgrade.api.adapters import IUpgradableZopeApp
from ftw.upgrade.api.adapters import UpgradablePloneSite
from ftw.upgrade.api.adapters import UpgradableZopeApp
from ftw.upgrade.testing import FTW_UPGRADE_FIXTURE
from plone.app.testing import FunctionalTesting
from plone.app.testing import PloneSandboxLayer
from Products.CMFCore.utils import getToolByName
from unittest2 import TestCase
from zope.component import queryAdapter
from zope.configuration import xmlconfig
from zope.interface.verify import FunctionType
from zope.interface.verify import MethodTypes
from zope.interface.verify import verifyClass


class UpgradesRegistered(PloneSandboxLayer):

    defaultBases = (FTW_UPGRADE_FIXTURE,)

    def setUpZope(self, app, configurationContext):
        import ftw.upgrade.tests.profiles
        xmlconfig.file('configure.zcml', ftw.upgrade.tests.profiles,
                       context=configurationContext)

        import ftw.upgrade.tests.upgrades
        xmlconfig.file('foo.zcml', ftw.upgrade.tests.upgrades,
                       context=configurationContext)

        import ftw.upgrade.tests.upgrades
        xmlconfig.file('bar.zcml', ftw.upgrade.tests.upgrades,
                       context=configurationContext)


UPGRADES_REGISTERED = UpgradesRegistered()
UPGRADES_REGISTERED_FUNCTIONAL = FunctionalTesting(
    bases=(UPGRADES_REGISTERED,), name='FtwUpgrade.api.foo:Functional')



class ImplementsOnlyTestCase(TestCase):

    def assertImplementsOnly(self, iface, obj):
        descriptions = dict(iface.namesAndDescriptions(all=True))
        attrs = [a for a in dir(obj) if not a.startswith('__')]
        for name in attrs:
            attr = getattr(obj, name)
            if isinstance(attr, FunctionType) or isinstance(attr, MethodTypes):
                desc = descriptions.get(name)
                if not desc:
                    self.fail("Undeclared method: '%s.%s'" % (iface.__name__, name))


class TestUpgradableZopeApp(ImplementsOnlyTestCase):

    layer = UPGRADES_REGISTERED_FUNCTIONAL

    def test_component_is_registered(self):
        app = self.layer['portal'].getPhysicalRoot()
        upgradable_app = queryAdapter(app, IUpgradableZopeApp)
        self.assertNotEqual(upgradable_app, None)

    def test_implements_interface(self):
        verifyClass(IUpgradableZopeApp, UpgradableZopeApp)
        self.assertImplementsOnly(IUpgradableZopeApp, UpgradableZopeApp)

    def test_get_plone_sites_lists_all_plone_sites(self):
        portal = self.layer['portal']
        zope_app = aq_parent(portal)
        upgradbable_app = queryAdapter(zope_app, IUpgradableZopeApp)
        self.assertEquals(upgradbable_app.get_plone_sites(), [portal.id])

    def test_get_plone_sites_only_upgradable_sites_when_asked_to(self):
        profileid = 'ftw.upgrade.tests.profiles:foo'
        portal = self.layer['portal']
        setup_tool = getToolByName(portal, 'portal_setup')

        zope_app = aq_parent(portal)
        upgradbable_app = queryAdapter(zope_app, IUpgradableZopeApp)
        self.assertEquals(upgradbable_app.get_plone_sites(upgradable=True), [])

        # Make one upgrade proposed -> site should be upgradable
        setup_tool.setLastVersionForProfile(profileid, '1')
        self.assertEquals(upgradbable_app.get_plone_sites(upgradable=True),
            [portal.id])

class TestUpgradablePloneSite(ImplementsOnlyTestCase):

    layer = UPGRADES_REGISTERED_FUNCTIONAL

    def test_component_is_registered(self):
        upgradable_site = queryAdapter(self.layer['portal'],
            IUpgradablePloneSite)
        self.assertNotEqual(upgradable_site, None)

    def test_implements_interface(self):
        verifyClass(IUpgradablePloneSite, UpgradablePloneSite)
        self.assertImplementsOnly(IUpgradablePloneSite, UpgradablePloneSite)

    def test_site_with_proposed_upgrades_is_upgradable(self):
        profileid = 'ftw.upgrade.tests.profiles:foo'
        setup_tool = getToolByName(self.layer['portal'], 'portal_setup')

        setup_tool.setLastVersionForProfile(profileid, '1')

        # We got one proposed upgrade, therefore the site should be upgradable
        upgradable_site = queryAdapter(self.layer['portal'],
                                        IUpgradablePloneSite)

        self.assertTrue(upgradable_site.is_upgradable())

    def test_site_without_proposed_upgrades_is_not_upgradable(self):
        upgradable_site = queryAdapter(self.layer['portal'],
                                        IUpgradablePloneSite)

        self.assertFalse(upgradable_site.is_upgradable())

    def test_lists_proposed_upgrades(self):
        profileid = 'ftw.upgrade.tests.profiles:foo'
        setup_tool = getToolByName(self.layer['portal'], 'portal_setup')

        upgrades = setup_tool.listUpgrades(profileid)
        self.assertEqual(len(upgrades), 1)

        # Initialize profile version to get it recognized as installed
        setup_tool.setLastVersionForProfile(profileid, '1')
        upgradable_site = queryAdapter(self.layer['portal'],
                                        IUpgradablePloneSite)

        proposed_upgrades = upgradable_site.get_upgrades()
        self.assertEquals(len(upgrades), len(proposed_upgrades))

    def test_lists_only_proposed_upgrades_by_default(self):
        foo_profile = 'ftw.upgrade.tests.profiles:foo'
        bar_profile = 'ftw.upgrade.tests.profiles:bar'
        setup_tool = getToolByName(self.layer['portal'], 'portal_setup')

        upgrades = setup_tool.listUpgrades(foo_profile)
        self.assertEqual(len(upgrades), 1)

        # Initialize profile version to get it recognized as installed
        setup_tool.setLastVersionForProfile(foo_profile, '1')

        # Set profile version to 2 so none of the upgrades should be proposed
        setup_tool.setLastVersionForProfile(bar_profile, '2')

        upgradable_site = queryAdapter(self.layer['portal'],
                                        IUpgradablePloneSite)

        proposed_upgrades = upgradable_site.get_upgrades()
        self.assertEquals(len(proposed_upgrades), 1)

    def test_lists_all_upgrades_if_asked_to(self):
        foo_profile = 'ftw.upgrade.tests.profiles:foo'
        bar_profile = 'ftw.upgrade.tests.profiles:bar'
        setup_tool = getToolByName(self.layer['portal'], 'portal_setup')

        upgrades = setup_tool.listUpgrades(foo_profile)
        self.assertEqual(len(upgrades), 1)

        # Initialize profile version to get it recognized as installed
        setup_tool.setLastVersionForProfile(foo_profile, '1')

        # Set profile version to 2 so none of the upgrades should be proposed
        setup_tool.setLastVersionForProfile(bar_profile, '2')

        upgradable_site = queryAdapter(self.layer['portal'],
                                        IUpgradablePloneSite)

        listed_upgrades = upgradable_site.get_upgrades(proposed=False)
        # Reduce list to only our testing profiles and filter out
        # common Plone profiles
        listed_upgrades = filter(
            lambda x: 'ftw.upgrade.tests.profiles' in x['id'], listed_upgrades)

        self.assertEquals(len(listed_upgrades), 2)

    def test_set_profile_version(self):
        profileid = 'ftw.upgrade.tests.profiles:foo'
        setup_tool = getToolByName(self.layer['portal'], 'portal_setup')

        original_version = setup_tool.getLastVersionForProfile(profileid)
        self.assertEquals(original_version, 'unknown')

        upgradable_site = queryAdapter(self.layer['portal'],
                                        IUpgradablePloneSite)

        retval = upgradable_site.set_profile_version(profileid, '1')
        new_version = setup_tool.getLastVersionForProfile(profileid)
        self.assertEquals(new_version, (u'1',))
        self.assertEquals(retval, [u'1'])

    def test_set_profile_version_raises_if_profile_version_is_invalid(self):
        upgradable_site = queryAdapter(self.layer['portal'],
                                        IUpgradablePloneSite)

        with self.assertRaises(Exception):
            upgradable_site.set_profile_version('invalid (no colon)', '1')

        with self.assertRaises(Exception):
            upgradable_site.set_profile_version('a:b:c', '1')
