from ftw.upgrade.api.adapters import IUpgradablePloneSite
from ftw.upgrade.api.adapters import IUpgradableZopeApp
from ftw.upgrade.interfaces import IExecutioner
from ftw.upgrade.utils import pretty_json
from Products.CMFCore.utils import getToolByName
from zope.component import getAdapter
from zope.component import queryAdapter
from zope.publisher.browser import BrowserView
import logging


log = logging.getLogger('ftw.upgrade')


class CoreAPI(object):
    """The core ftw.upgrade API.
    """
    def __init__(self, app):
        self.app = app

    def list_plone_sites(self, upgradable=False):
        """Return all the Plone sites in the Zope application root.
        """
        upgradable_app = queryAdapter(self.app, IUpgradableZopeApp)
        results = upgradable_app.get_plone_sites(upgradable=upgradable)
        return results

    def list_upgrades(self, plone_site_id, proposed=True):
        """List proposed upgrades for the given Plone site.

        If `proposed` is False, *all* upgrades, proposed or not, will be listed.
        """
        portal = self.app.restrictedTraverse(plone_site_id)
        upgradable_site = queryAdapter(portal, IUpgradablePloneSite)
        results = upgradable_site.get_upgrades(proposed=proposed)
        results = list(results)
        return results

    def run_upgrades(self, plone_site_id, proposed=True):
        """Run proposed upgrades for the given Plone site.

        If `proposed` is False, *all* upgrades, proposed or not, will be run.
        """
        portal = self.app.restrictedTraverse(plone_site_id)
        profiles = self.list_upgrades(plone_site_id, proposed=proposed)

        # upgrade_instructions is a list of key/value tuples where the key is a
        # profileid and the value is a list of upgrade ids.

        upgrade_instructions = []
        for profile in profiles:
            upgrade_ids = [u['id'] for u in profile['upgrades']]
            upgrade_instructions.append((profile['id'], upgrade_ids))

        gstool = getToolByName(portal, 'portal_setup')
        executioner = getAdapter(gstool, IExecutioner)
        executioner.install(upgrade_instructions)

        return {'status': 'SUCCESS'}


    def run_all_upgrades(self):
        """Run all proposed upgrades for all Plone sites.
        """
        results = {}
        for site_id in self.list_plone_sites():
            results[site_id] = self.run_upgrades(site_id, proposed=True)
        return results

    def set_profile_version(self, plone_site_id, profile_id, version):
        """Set DB version for a particular profile.
        """
        portal = self.app.restrictedTraverse(plone_site_id)
        upgradable_site = queryAdapter(portal, IUpgradablePloneSite)
        results = upgradable_site.set_profile_version(profile_id=profile_id,
                                                      version=version)
        results = list(results)
        return results


class JsonAPIView(BrowserView):
    """The ftw.upgrade JSON API.
    """

    #security = ClassSecurityInformation()

    def __init__(self, *args, **kwargs):
        super(JsonAPIView, self).__init__(*args, **kwargs)
        self.app = self.context
        self.core_api = CoreAPI(self.context)

    def __call__(self):
        __doc__ = """
        ftw.upgrade JSON API commands are available as traversable methods on
        the @@upgrade-api view:

        @@upgrade-api/list_sites
        @@upgrade-api/list_upgrades?site=[site_id]
        @@upgrade-api/run_all_upgrades
        @@upgrade-api/set_profile_version
        """
        return __doc__

    def _parse_bool(self, param_name):
        value = True
        _value = self.request.form.get(param_name)
        if _value.lower() == 'false' or not _value:
            value = False
        return value

    @pretty_json
    def list_sites(self):
        """List all Plone sites.
        """
        upgradable = self._parse_bool('upgradable')
        return self.core_api.list_plone_sites(upgradable=upgradable)

    @pretty_json
    def list_upgrades(self):
        """List all proposed upgrades for all Plone sites.
        """
        site = self.request.form.get('site')
        proposed = self._parse_bool('proposed')
        if site:
            return self._list_upgrades_for(site, proposed=proposed)
        else:
            return self._list_all_upgrades(proposed=proposed)

    @pretty_json
    def run_all_upgrades(self):
        """Run all proposed upgrades for all Plone sites.
        """
        return self.core_api.run_all_upgrades()

    def _list_upgrades_for(self, site_id, proposed=False):
        """List all proposed upgrades for a specific Plone site.
        """
        result = {}
        log.info("Upgrading Plone site '%s'..." % site_id)
        result[site_id] = self.core_api.list_upgrades(site_id,
                                                      proposed=proposed)
        return result

    def _list_all_upgrades(self, proposed=False):
        """List all proposed upgrades for all Plone sites.
        """
        result = {}
        plone_sites = self.core_api.list_plone_sites()

        for site_id in plone_sites:
            log.info("Upgrading Plone site '%s'..." % site_id)
            result[site_id] = self.core_api.list_upgrades(site_id,
                                                          proposed=proposed)
        return result

    @pretty_json
    def set_profile_version(self):
        """Set DB version for a particular profile.
        """
        site = self.request.form.get('site')
        profile = self.request.form.get('profile')
        version = self.request.form.get('version')

        if site:
            return self.core_api.set_profile_version(site, profile, version)

