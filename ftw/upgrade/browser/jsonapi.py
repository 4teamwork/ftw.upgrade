from AccessControl.requestmethod import requestmethod
from ftw.upgrade.interfaces import IUpgradeInformationGatherer
from operator import itemgetter
from Products.CMFCore.utils import getToolByName
from zope.component import getAdapter
from zope.publisher.browser import BrowserView
import json


class PloneSiteAPI(BrowserView):

    def __init__(self, *args, **kwargs):
        super(PloneSiteAPI, self).__init__(*args, **kwargs)
        self.portal_setup = getToolByName(self.context, 'portal_setup')
        self.gatherer = IUpgradeInformationGatherer(self.portal_setup)

    @requestmethod('GET')
    def get_profile(self, profileid, REQUEST=None):
        """Returns a JSON-encoded dict representation of the Generic Setup
        profile with the given ``id``.
        """

        return self._pretty_json(
            self._refine_profile_info(
                self._get_profile_info(profileid)))

    @requestmethod('GET')
    def list_profiles_proposing_upgrades(self, REQUEST=None):
        """Returns a list of profiles with proposed upgrade steps, only
        containing the proposed upgrade steps for each profile.
        """

        return self._pretty_json(
            map(self._refine_profile_info,
                self._get_profiles_proposing_upgrades()))

    def _refine_profile_info(self, profile):
        return {'id': profile['id'],
                'title': profile['title'],
                'product': profile['product'],
                'db_version': profile['db_version'],
                'fs_version': profile['version'],
                'outdated_fs_version': False,
                'upgrades': [self._refine_upgrade_info(profile, upgrade)
                             for upgrade in profile['upgrades']]}

    def _refine_upgrade_info(self, profile, upgrade):
        keys = ('title', 'proposed', 'done', 'orphan', 'outdated_fs_version')
        values = dict((key, value) for (key, value) in upgrade.items()
                      if key in keys)
        values.update({'id': '{0}@{1}'.format(upgrade['sdest'], profile['id']),
                       'title': upgrade['title'],
                       'source': upgrade['ssource'],
                       'dest': upgrade['sdest']})
        return values

    def _get_profile_info(self, profileid):
        profiles = filter(lambda profile: profile['id'] == profileid,
                          self.gatherer.get_upgrades())
        if len(profiles) == 0:
            return {}
        else:
            return profiles[0]

    def _get_profiles_proposing_upgrades(self):
        profiles = map(self._filter_proposed_upgrades_in_profile,
                       self.gatherer.get_upgrades())
        return filter(itemgetter('upgrades'), profiles)

    def _filter_proposed_upgrades_in_profile(self, profileinfo):
        profileinfo['upgrades'] = filter(itemgetter('proposed'),
                                         profileinfo['upgrades'])
        return profileinfo

    def _pretty_json(self, data):
        return json.dumps(data, indent=4)
