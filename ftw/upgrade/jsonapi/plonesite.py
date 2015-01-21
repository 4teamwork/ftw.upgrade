from ftw.upgrade.browser.manage import ResponseLogger
from ftw.upgrade.interfaces import IExecutioner
from ftw.upgrade.interfaces import IUpgradeInformationGatherer
from ftw.upgrade.jsonapi.base import APIView
from ftw.upgrade.jsonapi.exceptions import AbortTransactionWithStreamedResponse
from ftw.upgrade.jsonapi.exceptions import PloneSiteOutdated
from ftw.upgrade.jsonapi.exceptions import ProfileNotFound
from ftw.upgrade.jsonapi.utils import action
from ftw.upgrade.jsonapi.utils import jsonify
from operator import itemgetter
from Products.CMFCore.utils import getToolByName


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
        return map(self._refine_profile_info, self.gatherer.get_profiles())

    @jsonify
    @action('GET')
    def list_profiles_proposing_upgrades(self):
        """Returns a list of profiles with proposed upgrade steps.
        The upgrade steps of each profile only include proposed upgrades.
        """
        return map(self._refine_profile_info,
                   self.gatherer.get_profiles(proposed_only=True))

    @jsonify
    @action('GET')
    def list_proposed_upgrades(self):
        """Returns a list of proposed upgrades.
        """
        return map(self._refine_upgrade_info, self._get_proposed_upgrades())

    @action('POST', rename_params={'upgrades': 'upgrades:list'})
    def execute_upgrades(self, upgrades):
        """Executes a list of upgrades, each identified by the upgrade ID
        in the form "[dest-version]@[profile ID]".
        """
        self._require_up_to_date_plone_site()
        self._validate_upgrade_ids(*upgrades)
        return self._install_upgrades(*upgrades)

    @action('POST')
    def execute_proposed_upgrades(self):
        """Executes all proposed upgrades.
        """
        self._require_up_to_date_plone_site()
        api_ids = map(itemgetter('api_id'), self._get_proposed_upgrades())
        return self._install_upgrades(*api_ids)

    def _refine_profile_info(self, profile):
        return {'id': profile['id'],
                'title': profile['title'],
                'product': profile['product'],
                'db_version': profile['db_version'],
                'fs_version': profile['version'],
                'outdated_fs_version': False,
                'upgrades': map(self._refine_upgrade_info,
                                profile['upgrades'])}

    def _refine_upgrade_info(self, upgrade):
        keys = ('title', 'proposed', 'done', 'orphan', 'outdated_fs_version')
        values = dict((key, value) for (key, value) in upgrade.items()
                      if key in keys)
        values.update({'id': upgrade['api_id'],
                       'title': upgrade['title'],
                       'source': upgrade['ssource'],
                       'dest': upgrade['sdest']})
        return values

    def _get_profile_info(self, profileid):
        profiles = filter(lambda profile: profile['id'] == profileid,
                          self.gatherer.get_profiles())
        if len(profiles) == 0:
            raise ProfileNotFound(profileid)
        else:
            return profiles[0]

    def _get_proposed_upgrades(self):
        profiles = self.gatherer.get_profiles(proposed_only=True)
        if not profiles:
            return []
        return reduce(list.__add__, map(itemgetter('upgrades'), profiles))

    def _validate_upgrade_ids(self, *api_ids):
        self.gatherer.get_upgrades_by_api_ids(*api_ids)

    def _install_upgrades(self, *api_ids):
        executioner = IExecutioner(self.portal_setup)
        try:
            with ResponseLogger(self.request.RESPONSE, annotate_result=True):
                executioner.install_upgrades_by_api_ids(*api_ids)
        except Exception, exc:
            raise AbortTransactionWithStreamedResponse(exc)

    def _require_up_to_date_plone_site(self):
        portal_migration = getToolByName(self.context, 'portal_migration')
        if portal_migration.needUpgrading():
            raise PloneSiteOutdated()
