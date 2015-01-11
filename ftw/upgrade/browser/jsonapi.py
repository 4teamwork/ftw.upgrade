from AccessControl.requestmethod import requestmethod
from contextlib import contextmanager
from ftw.upgrade.interfaces import IExecutioner
from ftw.upgrade.interfaces import IUpgradeInformationGatherer
from operator import itemgetter
from Products.CMFCore.utils import getToolByName
from StringIO import StringIO
from zope.publisher.browser import BrowserView
import json
import logging


REQUIRED = object()


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
        with ErrorHandling(self.request.response):
            self._require_params(profileid=profileid)
            return self._json_for_response(
                self._refine_profile_info(
                    self._get_profile_info(profileid)))

    @requestmethod('GET')
    def list_profiles(self, REQUEST=None):
        """Returns a list of all installed profiles and their upgrade steps.
        """
        with ErrorHandling(self.request.response):
            return self._json_for_response(
                map(self._refine_profile_info,
                    self.gatherer.get_upgrades()))

    @requestmethod('GET')
    def list_profiles_proposing_upgrades(self, REQUEST=None):
        """Returns a list of profiles with proposed upgrade steps, only
        containing the proposed upgrade steps for each profile.
        """
        with ErrorHandling(self.request.response):
            return self._json_for_response(
                map(self._refine_profile_info,
                    self._get_profiles_proposing_upgrades()))

    @requestmethod('POST')
    def execute_upgrades(self, upgrades=REQUIRED, REQUEST=None):
        """Execute a list of upgrades, each identified by the upgrade ID
        returned by the profile listing actions
        (``[dest-version]@[profile ID]``).
        """
        with ErrorHandling(self.request.response):
            self._require_up_to_date_plone_site()
            self._require_params(**{'upgrades:list': upgrades})
            upgrade_infos = self._get_upgrades_by_api_ids(upgrades)
            return self._install_upgrades(upgrade_infos)

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

    def _install_upgrades(self, upgrades):
        data = [(upgrade['profile'], [upgrade['id']]) for upgrade in upgrades]
        executioner = IExecutioner(self.portal_setup)
        with capture_log() as stream:
            executioner.install(data)
        return stream.getvalue()

    def _get_upgrades_by_api_ids(self, api_upgrade_ids):
        profiles = self.gatherer.get_upgrades()
        upgrades = [self._get_upgrades_by_api_id(api_id, profiles)
                    for api_id in self._order_upgrade_ids(api_upgrade_ids)]
        return reduce(list.__add__, upgrades)

    def _order_upgrade_ids(self, api_upgrade_ids):
        ordered_upgrade_ids = []
        for profile in self.gatherer.get_upgrades():
            for upgrade in profile['upgrades']:
                ordered_upgrade_ids.append('{0}@{1}'.format(upgrade['sdest'],
                                                            profile['id']))

        not_found = set(api_upgrade_ids) - set(ordered_upgrade_ids)
        if not_found:
            raise UpgradeNotFound(tuple(not_found)[0])

        return list(sorted(api_upgrade_ids, key=ordered_upgrade_ids.index))

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

    def _json_for_response(self, data):
        response = self.request.response
        response.setHeader('Content-Type', 'application/json; charset=utf-8')
        return json.dumps(data, indent=4, encoding='utf-8')

    def _require_params(self, **params):
        for name, value in params.items():
            if value is REQUIRED:
                raise MissingParam(name)

    def _require_up_to_date_plone_site(self):
        portal_migration = getToolByName(self.context, 'portal_migration')
        if portal_migration.needUpgrading():
            raise PloneSiteOutdated()


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


class ErrorHandling(object):
    def __init__(self, response):
        self.response = response

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc, traceback):
        if not isinstance(exc, APIError):
            return

        self.response.setStatus(exc.response_code, exc.message)
        self.response.setHeader('Content-Type',
                                'application/json; charset=utf-8')
        self.response.setBody(json.dumps(['ERROR', exc.message, exc.details]))
        self.response.flush()
        return True


class APIError(Exception):
    def __init__(self, message, details='', response_code=400):
        super(APIError, self).__init__(message)
        self.message = message
        self.details = details
        self.response_code = response_code


class MissingParam(APIError):
    def __init__(self, param_name):
        super(MissingParam, self).__init__(
            'Param missing',
            'The param "{0}" is required for this API action.'.format(
                param_name))


class PloneSiteOutdated(APIError):
    def __init__(self):
        super(PloneSiteOutdated, self).__init__(
            'Plone site outdated',
            'The Plone site is outdated and needs to be upgraded'
            ' first using the regular Plone upgrading tools.')


class UpgradeNotFound(APIError):
    def __init__(self, api_upgrade_id):
        super(UpgradeNotFound, self).__init__(
            'Upgrade not found',
            'The upgrade "{0}" is unkown.'.format(api_upgrade_id))
