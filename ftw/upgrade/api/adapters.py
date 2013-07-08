from OFS.interfaces import IApplication
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.interfaces import IPloneSiteRoot
from zope.component import adapts
from zope.interface import implements
from zope.component import queryAdapter
from ftw.upgrade.interfaces import IUpgradeInformationGatherer
from ftw.upgrade.exceptions import CyclicDependencies


from ftw.upgrade.api.interfaces import IUpgradablePloneSite
from ftw.upgrade.api.interfaces import IUpgradableZopeApp
from ftw.upgrade.exceptions import APIError


class UpgradablePloneSite(object):
    """Adapter to expose ftw.upgrade functionality for a Plone site.
    """
    implements(IUpgradablePloneSite)
    adapts(IPloneSiteRoot)

    def __init__(self, plone_site):
        self.portal = plone_site

    def is_upgradable(self):
        """True if the site has proposed upgrades, false otherwise.
        """
        upgradable = list(self.get_proposed_upgrades()) != []
        return upgradable

    def get_upgrades(self, proposed=True):
        """List upgrades for the adapted Plone site.

        If `proposed` is True (default), only proposed upgrades will be returned.
        Otherwise all the upgrades will be listed.
        """

        def proposed_only(profiles):
            """Filter a list of profiles with upgrades to contain only proposed
            upgrades.
            """
            for profile in profiles:
                # Iterate over a copy of the list so we don't change list size
                # during iteration
                for upgrade in profile['upgrades'][:]:
                    if not upgrade['proposed']:
                        profile['upgrades'].remove(upgrade)
                if not profile['upgrades'] == []:
                    # Only yield profiles with at least one proposed upgrade
                    yield profile

        gstool = getToolByName(self.portal, 'portal_setup')
        gatherer = queryAdapter(gstool, IUpgradeInformationGatherer)
        if not gatherer:
            raise APIError("Could not find gatherer for %s." % self.portal)
        try:
            profiles = gatherer.get_upgrades()
            if proposed:
                return list(proposed_only(profiles))
            else:
                return profiles

        except CyclicDependencies, exc:
            print exc.dependencies
            raise exc

    # def execute_upgrades(self):
    #     raise NotImplemented


class UpgradableZopeApp(object):
    """Adapter to expose ftw.upgrade functionality for a Zope application root.
    """
    implements(IUpgradableZopeApp)
    adapts(IApplication)

    def __init__(self, context):
        self.app = context

    def get_plone_sites(self, upgradable=False):
        """List all Plone sites.

        If `upgradable` is True, only lists sites that have proposed upgrades.
        """
        site_ids = []
        for item_id, item in self.app.items():
            if IPloneSiteRoot.providedBy(item):
                if upgradable:
                    # Only list plone sites with at least one proposed upgrade
                    site = self.app.restrictedTraverse(item_id)
                    upgradable_site = IUpgradablePloneSite(site)
                    if upgradable_site.is_upgradable():
                        site_ids.append(item_id)
                else:
                    # List all sites regardless if upgradable
                    site_ids.append(item_id)
        return site_ids

    # def execute_upgrades_for_sites(self):
    #     raise NotImplemented
