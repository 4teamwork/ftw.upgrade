from ftw.builder.testing import BUILDER_LAYER
from ftw.builder.testing import functional_session_factory
from ftw.builder.testing import set_builder_session_factory
from ftw.testing.layer import COMPONENT_REGISTRY_ISOLATION
from ftw.testing.layer import ConsoleScriptLayer
from ftw.testing.layer import TEMP_DIRECTORY
from plone.app.testing import applyProfile
from plone.app.testing import FunctionalTesting
from plone.app.testing import PLONE_ZSERVER
from plone.app.testing import PloneSandboxLayer
from plone.testing import z2
from zope.configuration import xmlconfig
import ftw.upgrade.tests.builders


COMMAND_LAYER = ConsoleScriptLayer('ftw.upgrade',
                                   bases=(BUILDER_LAYER, ),
                                   name='ftw.upgrade:command')


class UpgradeLayer(PloneSandboxLayer):
    defaultBases = (COMPONENT_REGISTRY_ISOLATION,
                    BUILDER_LAYER,
                    TEMP_DIRECTORY)

    def setUpZope(self, app, configurationContext):
        import Products.CMFPlacefulWorkflow
        xmlconfig.file('configure.zcml', Products.CMFPlacefulWorkflow,
                       context=configurationContext)

        import ftw.upgrade
        xmlconfig.file('configure.zcml', ftw.upgrade,
                       context=configurationContext)

        z2.installProduct(app, 'Products.CMFPlacefulWorkflow')

    def setUpPloneSite(self, portal):
        applyProfile(
            portal, 'Products.CMFPlacefulWorkflow:CMFPlacefulWorkflow')
        applyProfile(portal, 'ftw.upgrade:default')


UPGRADE_LAYER = UpgradeLayer()
UPGRADE_FUNCTIONAL_TESTING = FunctionalTesting(
    bases=(UPGRADE_LAYER,
           set_builder_session_factory(functional_session_factory)),
    name="ftw.upgrade:functional")

COMMAND_AND_UPGRADE_FUNCTIONAL_TESTING = FunctionalTesting(
    bases=(PLONE_ZSERVER,
           UPGRADE_LAYER,
           set_builder_session_factory(functional_session_factory),
           COMMAND_LAYER),
    name="ftw.upgrade:command_and_functional")
