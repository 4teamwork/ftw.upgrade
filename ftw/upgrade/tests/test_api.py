from ftw.upgrade.api.adapters import IUpgradablePloneSite
from ftw.upgrade.api.adapters import IUpgradableZopeApp
from ftw.upgrade.api.adapters import UpgradablePloneSite
from ftw.upgrade.api.adapters import UpgradableZopeApp
from ftw.upgrade.testing import FTW_UPGRADE_FIXTURE
from plone.app.testing import FunctionalTesting
from plone.app.testing import PloneSandboxLayer
from unittest2 import TestCase
from zope.component import queryAdapter
from zope.configuration import xmlconfig
from zope.interface.verify import FunctionType
from zope.interface.verify import MethodTypes
from zope.interface.verify import verifyClass


class UpgradesRegistered(PloneSandboxLayer):

    defaultBases = (FTW_UPGRADE_FIXTURE,)

    def setUpZope(self, app, configurationContext):
        import ftw.upgrade.tests.upgrades
        xmlconfig.file('foo.zcml', ftw.upgrade.tests.upgrades,
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


class TestUpgradablePloneSite(ImplementsOnlyTestCase):

    layer = UPGRADES_REGISTERED_FUNCTIONAL

    def test_component_is_registered(self):
        upgradable_site = queryAdapter(self.layer['portal'], IUpgradablePloneSite)
        self.assertNotEqual(upgradable_site, None)

    def test_implements_interface(self):
        verifyClass(IUpgradablePloneSite, UpgradablePloneSite)
        self.assertImplementsOnly(IUpgradablePloneSite, UpgradablePloneSite)

