from ftw.builder.testing import BUILDER_LAYER
from ftw.builder.testing import functional_session_factory
from ftw.builder.testing import set_builder_session_factory
from ftw.testing.layer import COMPONENT_REGISTRY_ISOLATION
from ftw.testing.layer import ConsoleScriptLayer
from ftw.testing.layer import TEMP_DIRECTORY
from operator import itemgetter
from plone.app.testing import applyProfile
from plone.app.testing import FunctionalTesting
from plone.app.testing import PLONE_ZSERVER
from plone.app.testing import PloneSandboxLayer
from plone.testing import z2
from Products.CMFCore.utils import getToolByName
from Products.SiteAccess.VirtualHostMonster import manage_addVirtualHostMonster
from zope.configuration import xmlconfig
import ftw.upgrade.tests.builders
import pkg_resources


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

        manage_addVirtualHostMonster(app, 'virtual_hosting')

    def setUpPloneSite(self, portal):
        applyProfile(
            portal, 'Products.CMFPlacefulWorkflow:CMFPlacefulWorkflow')
        applyProfile(portal, 'ftw.upgrade:default')

        self.fix_plone_app_jquery_version(portal)

    def fix_plone_app_jquery_version(self, portal):
        try:
            pkg_resources.get_distribution('plone.app.jquery')
        except pkg_resources.DistributionNotFound:
            return

        # The plone.app.jquery version shipped with Plone 4.2 has an outdated
        # metadata.xml version, resulting in proposed upgrades in a fresh
        # installation.
        # For consistent test result we fix that here.
        portal_setup = getToolByName(portal, 'portal_setup')
        profileid = 'plone.app.jquery:default'
        version = max(map(itemgetter('dest'),
                          portal_setup.listUpgrades(profileid, show_old=True)))
        portal_setup.setLastVersionForProfile(profileid, version)


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
