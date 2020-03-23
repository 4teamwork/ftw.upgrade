from ftw.builder.testing import BUILDER_LAYER
from ftw.builder.testing import functional_session_factory
from ftw.builder.testing import set_builder_session_factory
from ftw.testbrowser import browser
from ftw.testing.layer import COMPONENT_REGISTRY_ISOLATION
from ftw.testing.layer import ConsoleScriptLayer
from ftw.testing.layer import TEMP_DIRECTORY
from operator import itemgetter
from plone.app.testing import applyProfile
from plone.app.testing import FunctionalTesting
from plone.app.testing import PLONE_ZSERVER
from plone.app.testing import PloneSandboxLayer
from plone.app.testing import SITE_OWNER_NAME
from plone.registry.interfaces import IRegistry
from plone.testing import z2
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.utils import getFSVersionTuple
from Products.SiteAccess.VirtualHostMonster import manage_addVirtualHostMonster
from six.moves import map
from zope.component import getUtility
from zope.configuration import xmlconfig

import ftw.upgrade.tests.builders
import pkg_resources
import transaction


ftw.upgrade.tests.builders  # pyflakes


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

        z2.installProduct(app, 'Products.DateRecurringIndex')
        import plone.app.contenttypes
        xmlconfig.file('configure.zcml', plone.app.contenttypes,
                       context=configurationContext)

        z2.installProduct(app, 'Products.CMFPlacefulWorkflow')

        try:
            # Plone 4 with collective.indexing
            pkg_resources.get_distribution('collective.indexing')
        except pkg_resources.DistributionNotFound:
            pass
        else:
            import collective.indexing
            xmlconfig.file('configure.zcml', collective.indexing,
                           context=configurationContext)
            z2.installProduct(app, 'collective.indexing')

        manage_addVirtualHostMonster(app, 'virtual_hosting')

    def setUpPloneSite(self, portal):
        if getFSVersionTuple() > (5, ):
            applyProfile(portal, 'plone.app.contenttypes:default')

        applyProfile(
            portal, 'Products.CMFPlacefulWorkflow:CMFPlacefulWorkflow')
        applyProfile(portal, 'ftw.upgrade:default')

        self.fix_plone_app_jquery_version(portal)
        self.prevent_csrf_by_initializing_site_storages(portal)

        # Enable development mode so that resources are included in separately
        # in the HTML so that we can test for recooked resources.
        registry = getUtility(IRegistry)
        if 'plone.resources.development' in registry:
            registry['plone.resources.development'] = True

    def prevent_csrf_by_initializing_site_storages(self, portal):
        """Plone auto-protection results in confirmation pages
        when first hitting Plone with the browser.

        By hitting the site once we can initialize all standard Plone
        containers which cause writes on first hit.
        We do this with disabled protection.
        """
        try:
            from plone.protect import auto
        except ImportError:
            return

        transaction.commit()
        with browser(portal.aq_inner.aq_parent):
            crsrf_disabled_ori = auto.CSRF_DISABLED
            auto.CSRF_DISABLED = True
            try:
                browser.login(SITE_OWNER_NAME).open(
                    view='overview-controlpanel')
            finally:
                auto.CSRF_DISABLED = crsrf_disabled_ori
                transaction.begin()

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


class IntIdUpgradeLayer(PloneSandboxLayer):

    defaultBases = (UPGRADE_LAYER, )

    def setUpZope(self, app, configurationContext):
        import plone.app.intid
        xmlconfig.file('configure.zcml', plone.app.intid,
                       context=configurationContext)

    def setUpPloneSite(self, portal):
        applyProfile(portal, 'plone.app.intid:default')


INTID_UPGRADE_LAYER = IntIdUpgradeLayer()
INTID_UPGRADE_FUNCTIONAL_TESTING = FunctionalTesting(
    bases=(INTID_UPGRADE_LAYER,
           set_builder_session_factory(functional_session_factory)),
    name="ftw.upgrade-intid:functional")
