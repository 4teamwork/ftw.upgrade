from ftw.builder.session import BuilderSession
from ftw.builder.testing import BUILDER_LAYER
from ftw.builder.testing import set_builder_session_factory
from ftw.testing.layer import ComponentRegistryLayer
from plone.app.testing import FunctionalTesting
from plone.app.testing import IntegrationTesting
from plone.app.testing import PLONE_FIXTURE
from plone.app.testing import PloneSandboxLayer
from plone.app.testing import applyProfile
from plone.app.testing import setRoles, TEST_USER_ID, TEST_USER_NAME, login
from plone.testing import z2
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


def functional_session_factory():
    sess = BuilderSession()
    sess.auto_commit = True
    return sess


class FtwUpgradeLayer(PloneSandboxLayer):

    defaultBases = (PLONE_FIXTURE, BUILDER_LAYER)

    def setUpZope(self, app, configurationContext):
        import Products.CMFPlacefulWorkflow
        xmlconfig.file('configure.zcml', Products.CMFPlacefulWorkflow,
                       context=configurationContext)

        import ftw.upgrade
        xmlconfig.file('configure.zcml', ftw.upgrade,
                       context=configurationContext)

        import ftw.upgrade.tests.profiles
        xmlconfig.file('configure.zcml', ftw.upgrade.tests.profiles,
                       context=configurationContext)

        import ftw.upgrade.tests.upgrades
        xmlconfig.file('navigation.zcml', ftw.upgrade.tests.upgrades,
                       context=configurationContext)

        z2.installProduct(app, 'Products.CMFPlacefulWorkflow')

    def setUpPloneSite(self, portal):
        applyProfile(
            portal, 'Products.CMFPlacefulWorkflow:CMFPlacefulWorkflow')
        applyProfile(portal, 'ftw.upgrade:default')

        setRoles(portal, TEST_USER_ID, ['Manager'])
        login(portal, TEST_USER_NAME)


FTW_UPGRADE_FIXTURE = FtwUpgradeLayer()
FTW_UPGRADE_INTEGRATION_TESTING = IntegrationTesting(
    bases=(FTW_UPGRADE_FIXTURE,), name="FtwUpgrade:Integration")
FTW_UPGRADE_FUNCTIONAL_TESTING = FunctionalTesting(
    bases=(FTW_UPGRADE_FIXTURE,
           set_builder_session_factory(functional_session_factory)),
    name='FtwUpgrade:Functional')


class CyclicDependenciesLayer(PloneSandboxLayer):

    defaultBases = (FTW_UPGRADE_FIXTURE,)

    def setUpZope(self, app, configurationContext):
        import ftw.upgrade.tests.profiles
        xmlconfig.file('cyclic-dependencies.zcml',
                       ftw.upgrade.tests.profiles,
                       context=configurationContext)


CYCLIC_DEPENDENCIES_FIXTURE = CyclicDependenciesLayer()
CYCLIC_DEPENDENCIES_FUNCTIONAL = FunctionalTesting(
    bases=(CYCLIC_DEPENDENCIES_FIXTURE, ),
    name='ftw.upgrade:cyclic-dependencies:functional')
