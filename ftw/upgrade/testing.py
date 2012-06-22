from ftw.testing.layer import ComponentRegistryLayer
from plone.app.testing import FunctionalTesting
from plone.app.testing import IntegrationTesting
from plone.app.testing import PloneSandboxLayer
from plone.app.testing import applyProfile
from plone.app.testing import setRoles, TEST_USER_ID, TEST_USER_NAME, login
from plone.testing import zca
from zope.configuration import xmlconfig


class ZCMLLayer(ComponentRegistryLayer):
    """A layer which only sets up the zcml, but does not start a zope
    instance.
    """

    defaultBases = (zca.ZCML_DIRECTIVES,)

    def setUp(self):
        super(ZCMLLayer, self).setUp()
        import ftw.upgrade.tests
        self.load_zcml_file('test.zcml', ftw.upgrade.tests)


ZCML_LAYER = ZCMLLayer()


class FtwUpgradeLayer(PloneSandboxLayer):

    def setUpZope(self, app, configurationContext):
        import ftw.upgrade
        xmlconfig.file('configure.zcml', ftw.upgrade,
                       context=configurationContext)

        import ftw.upgrade.tests.profiles
        xmlconfig.file('configure.zcml', ftw.upgrade.tests.profiles,
                       context=configurationContext)

        import ftw.upgrade.tests.upgrades
        xmlconfig.file('navigation.zcml', ftw.upgrade.tests.upgrades,
                       context=configurationContext)

    def setUpPloneSite(self, portal):
        applyProfile(portal, 'ftw.upgrade:default')

        setRoles(portal, TEST_USER_ID, ['Manager'])
        login(portal, TEST_USER_NAME)


FTW_UPGRADE_FIXTURE = FtwUpgradeLayer()
FTW_UPGRADE_INTEGRATION_TESTING = IntegrationTesting(
    bases=(FTW_UPGRADE_FIXTURE,), name="FtwUpgrade:Integration")
FTW_UPGRADE_FUNCTIONAL_TESTING = FunctionalTesting(
    bases=(FTW_UPGRADE_FIXTURE,), name='FtwUpgrade:Functional')
