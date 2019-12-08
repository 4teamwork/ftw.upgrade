from ftw.upgrade.browser.manage import ResponseLogger
from ftw.upgrade.interfaces import IExecutioner
from ftw.upgrade.interfaces import IUpgradeInformationGatherer
from ftw.upgrade.jsonapi.base import APIView
from ftw.upgrade.jsonapi.exceptions import AbortTransactionWithStreamedResponse
from ftw.upgrade.jsonapi.exceptions import PloneSiteOutdated
from ftw.upgrade.jsonapi.exceptions import ProfileNotAvailable
from ftw.upgrade.jsonapi.exceptions import ProfileNotFound
from ftw.upgrade.jsonapi.utils import action
from ftw.upgrade.jsonapi.utils import jsonify
from ftw.upgrade.jsonapi.utils import parse_bool
from ftw.upgrade.resource_registries import recook_resources
from ftw.upgrade.utils import get_portal_migration
from functools import reduce
from operator import itemgetter
from Products.CMFCore.utils import getToolByName
from six.moves import map


class PloneSiteAPI(APIView):

    def __init__(self, *args, **kwargs):
        super(PloneSiteAPI, self).__init__(*args, **kwargs)
        self.portal_setup = getToolByName(self.context, 'portal_setup')
        self.gatherer = IUpgradeInformationGatherer(self.portal_setup)

    @jsonify
    @action('GET')
    def get_profile(self, profileid):
        """Returns the profile with the id "profileid" as hash.
        """
        return self._refine_profile_info(self._get_profile_info(profileid))

    @jsonify
    @action('GET')
    def list_profiles(self):
        """Returns a list of all installed profiles.
        """
        return list(map(self._refine_profile_info, self.gatherer.get_profiles()))

    @jsonify
    @action('GET')
    def list_profiles_proposing_upgrades(self):
        """Returns a list of profiles with proposed upgrade steps.
        The upgrade steps of each profile only include proposed upgrades.
        """
        return list(map(self._refine_profile_info,
                        self.gatherer.get_profiles(proposed_only=True)))

    @jsonify
    @action('GET')
    def list_proposed_upgrades(self, propose_deferrable=True):
        """Returns a list of proposed upgrades.
        """
        propose_deferrable = parse_bool(propose_deferrable)
        return list(map(
            self._refine_upgrade_info,
            self._get_proposed_upgrades(propose_deferrable=propose_deferrable)))

    @action('POST', rename_params={'upgrades': 'upgrades:list'})
    def execute_upgrades(self, upgrades, allow_outdated=False):
        """Executes a list of upgrades, each identified by the upgrade ID
        in the form "[dest-version]@[profile ID]".
        """
        if not allow_outdated:
            self._require_up_to_date_plone_site()
        self._validate_upgrade_ids(*upgrades)
        return self._install_upgrades(*upgrades)

    @action('POST', rename_params={'profiles': 'profiles:list'})
    def execute_proposed_upgrades(self, profiles=None, propose_deferrable=True,
            allow_outdated=False):
        """Executes all proposed upgrades.
        """
        if not allow_outdated:
            self._require_up_to_date_plone_site()
        if profiles:
            self._validate_profile_ids(*profiles)
        propose_deferrable = parse_bool(propose_deferrable)

        api_ids = list(map(itemgetter('api_id'), self._get_proposed_upgrades(
            only_profiles=profiles, propose_deferrable=propose_deferrable)))
        return self._install_upgrades(
            *api_ids, propose_deferrable=propose_deferrable)

    @action('POST', rename_params={'profiles': 'profiles:list'})
    def execute_profiles(self, profiles, force_reinstall=False,
            allow_outdated=False):
        """Executes a list of profiles, each identified by their ID.
        """
        if not allow_outdated:
            self._require_up_to_date_plone_site()
        self._validate_profile_ids(*profiles)
        return self._install_profiles(*profiles,
                                      force_reinstall=force_reinstall)

    @jsonify
    @action('POST')
    def recook_resources(self):
        """Recook CSS and JavaScript resource bundles.
        """
        recook_resources()
        return 'OK'

    @jsonify
    @action('POST')
    def combine_bundles(self):
        """Combine JS/CSS bundles together.

        Since this is only for Plone 5 or higher, we do the import inline.
        The imported function was introduced in Plone 5.0.3.
        """
        from Products.CMFPlone.resources.browser.combine import combine_bundles

        combine_bundles(self.context)
        return 'OK'

    @jsonify
    @action('POST')
    def plone_upgrade(self):
        """Upgrade the Plone Site.

        This is what you would manually do in the @@plone-upgrade view.
        """
        portal_migration = get_portal_migration(self.context)
        if not portal_migration.needUpgrading():
            return 'Plone Site was already up to date.'
        portal_migration.upgrade(swallow_errors=False)
        return 'Plone Site has been updated.'

    @jsonify
    @action('GET')
    def plone_upgrade_needed(self):
        """Returns "true" when Plone needs to be upgraded.
        """
        portal_migration = get_portal_migration(self.context)
        return bool(portal_migration.needUpgrading())

    def _refine_profile_info(self, profile):
        return {'id': profile['id'],
                'title': profile['title'],
                'product': profile['product'],
                'db_version': profile['db_version'],
                'fs_version': profile['version'],
                'outdated_fs_version': False,
                'upgrades': list(map(self._refine_upgrade_info,
                                     profile['upgrades']))}

    def _refine_upgrade_info(self, upgrade):
        keys = ('title', 'proposed', 'deferrable', 'done', 'orphan',
                'outdated_fs_version')
        values = dict((key, value) for (key, value) in upgrade.items()
                      if key in keys)
        values.update({'id': upgrade['api_id'],
                       'title': upgrade['title'],
                       'source': upgrade['ssource'],
                       'dest': upgrade['sdest']})
        return values

    def _get_profile_info(self, profileid):
        profiles = [
            profile for profile in self.gatherer.get_profiles()
            if profile['id'] == profileid
        ]
        if len(profiles) == 0:
            raise ProfileNotAvailable(profileid)
        else:
            return profiles[0]

    def _get_proposed_upgrades(self, only_profiles=None, propose_deferrable=True):
        profiles = self.gatherer.get_profiles(proposed_only=True,
                                              propose_deferrable=propose_deferrable)
        if only_profiles:
            profiles = [
                profile for profile in profiles if profile['id'] in only_profiles]
        if not profiles:
            return []
        return reduce(list.__add__, map(itemgetter('upgrades'), profiles))

    def _validate_upgrade_ids(self, *api_ids):
        self.gatherer.get_upgrades_by_api_ids(*api_ids)

    def _validate_profile_ids(self, *profiles):
        for profile in profiles:
            # Note: profileExists can handle ids with or without 'profile-' at
            # the start.
            if not self.portal_setup.profileExists(profile):
                raise ProfileNotFound(profile)

    def _install_upgrades(self, *api_ids, **kwargs):
        propose_deferrable = kwargs.pop('propose_deferrable', True)
        executioner = IExecutioner(self.portal_setup)
        try:
            with ResponseLogger(self.request.RESPONSE, annotate_result=True):
                executioner.install_upgrades_by_api_ids(
                    *api_ids, propose_deferrable=propose_deferrable)
        except Exception as exc:
            raise AbortTransactionWithStreamedResponse(exc)

    def _install_profiles(self, *profile_ids, **options):
        executioner = IExecutioner(self.portal_setup)
        try:
            with ResponseLogger(self.request.RESPONSE, annotate_result=True):
                executioner.install_profiles_by_profile_ids(
                    *profile_ids, **options)
        except Exception as exc:
            raise AbortTransactionWithStreamedResponse(exc)

    def _require_up_to_date_plone_site(self):
        portal_migration = get_portal_migration(self.context)
        if portal_migration.needUpgrading():
            raise PloneSiteOutdated()
