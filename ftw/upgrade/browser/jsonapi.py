from AccessControl.requestmethod import requestmethod
from contextlib import contextmanager
from ftw.upgrade.interfaces import IExecutioner
from ftw.upgrade.interfaces import IUpgradeInformationGatherer
from operator import itemgetter
from Products.CMFCore.utils import getToolByName
from StringIO import StringIO
from zope.component import getAdapter
from zope.publisher.browser import BrowserView
import json
import logging


REQUIRED = object()


class UpgradeNotFound(Exception):
    def __init__(self, api_upgrade_id):
        super(UpgradeNotFound, self).__init__(api_upgrade_id)
        self.api_upgrade_id = api_upgrade_id


@contextmanager
def capture_log():
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    formatter = logging.root.handlers[-1].formatter
    handler.setFormatter(formatter)
    handler.setLevel(logging.INFO)

    original_level = logging.root.getEffectiveLevel()
    logging.root.addHandler(handler)
    logging.root.setLevel(logging.INFO)
    try:
        yield stream

    finally:
        stream.seek(0)
        logging.root.removeHandler(handler)
        logging.root.setLevel(original_level)


class PloneSiteAPI(BrowserView):

    def __init__(self, *args, **kwargs):
        super(PloneSiteAPI, self).__init__(*args, **kwargs)
        self.portal_setup = getToolByName(self.context, 'portal_setup')
        self.gatherer = IUpgradeInformationGatherer(self.portal_setup)

    @requestmethod('GET')
    def get_profile(self, profileid=REQUIRED, REQUEST=None):
        """Returns a JSON-encoded dict representation of the Generic Setup
        profile with the given ``id``.
        """
        if profileid is REQUIRED:
            return self._error(
                400, 'Missing "profileid" param in request.',
                'The "profileid" param is required for this action.'
                ' The value is expected to be a profile ID,'
                ' e.g. "my.package:default".')

        return self._pretty_json(
            self._refine_profile_info(
                self._get_profile_info(profileid)))

    @requestmethod('GET')
    def list_profiles(self, REQUEST=None):
        """Returns a list of all installed profiles and their upgrade steps.
        """

        return self._pretty_json(
            map(self._refine_profile_info,
                self.gatherer.get_upgrades()))

    @requestmethod('GET')
    def list_profiles_proposing_upgrades(self, REQUEST=None):
        """Returns a list of profiles with proposed upgrade steps, only
        containing the proposed upgrade steps for each profile.
        """

        return self._pretty_json(
            map(self._refine_profile_info,
                self._get_profiles_proposing_upgrades()))

    @requestmethod('POST')
    def execute_upgrades(self, upgrades=REQUIRED, REQUEST=None):
        """Execute a list of upgrades, each identified by the upgrade ID
        returned by the profile listing actions
        (``[dest-version]@[profile ID]``).
        """
        portal_migration = getToolByName(self.context, 'portal_migration')
        if portal_migration.needUpgrading():
            return self._error(
                400, 'Plone site outdated',
                'The Plone site is outdated and needs to be upgraded'
                ' first using the regular Plone upgrading tools.')

        if upgrades is REQUIRED:
            return self._error(
                400, 'Missing "upgrades:list" param in request.',
                'The "upgrades:list" param is required for this action.'
                ' It should be used once for each upgrade to execute and'
                ' contain the upgrade ID returned by the API,'
                ' e.g. "4023@my.package:default".')

        try:
            data = self._prepare_executioner_data_by_upgrade_ids(upgrades)
        except UpgradeNotFound, exc:
            return self._error(
                400, 'Upgrade ID not found',
                'The upgrade ID "{0}" could not be found.'.format(
                    exc.api_upgrade_id))

        executioner = IExecutioner(self.portal_setup)
        with capture_log() as stream:
            executioner.install(data)

        return stream.getvalue()

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

    def _prepare_executioner_data_by_upgrade_ids(self, api_upgrade_ids):
        gathered_profiles = self.gatherer.get_upgrades()

        # order api_upgrade_ids by gathered_profiles order
        ordered_upgrade_ids = []
        for profile in gathered_profiles:
            for upgrade in profile['upgrades']:
                ordered_upgrade_ids.append('{0}@{1}'.format(upgrade['sdest'],
                                                            profile['id']))

        not_found = set(api_upgrade_ids) - set(ordered_upgrade_ids)
        if not_found:
            raise UpgradeNotFound(tuple(not_found)[0])

        api_upgrade_ids.sort(key=ordered_upgrade_ids.index)

        # prepare data as accepted by executioner
        executioner_data = []
        for api_id in api_upgrade_ids:
            for upgrade in self._get_upgrades_by_api_id(api_id,
                                                        gathered_profiles):
                executioner_data.append((upgrade['profile'], [upgrade['id']]))

        return executioner_data

    def _get_upgrades_by_api_id(self, api_upgrade_id, profiles=None):
        if not profiles:
            profiles = self.gatherer.get_upgrades()
        profiles_map = dict([(profile['id'], profile) for profile in profiles])

        upgrade_sdest, profile_id = api_upgrade_id.split('@')
        if profile_id not in profiles_map:
            raise UpgradeNotFound(api_upgrade_id)

        upgrades = [upgrade for upgrade in profiles_map[profile_id]['upgrades']
                    if upgrade['sdest'] == upgrade_sdest]
        if len(upgrades) == 0:
            raise UpgradeNotFound(api_upgrade_id)

        for upgrade in upgrades:
            upgrade['profile'] = profile_id
        return upgrades

    def _pretty_json(self, data):
        return json.dumps(data, indent=4)

    def _error(self, status, message, details=''):
        self.request.response.setStatus(status, message)
        return json.dumps(['ERROR', message, details])
