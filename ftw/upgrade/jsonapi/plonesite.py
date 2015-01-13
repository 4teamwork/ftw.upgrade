from contextlib import contextmanager
from ftw.upgrade.interfaces import IExecutioner
from ftw.upgrade.interfaces import IUpgradeInformationGatherer
from ftw.upgrade.jsonapi.exceptions import PloneSiteOutdated
from ftw.upgrade.jsonapi.utils import action
from ftw.upgrade.jsonapi.utils import jsonify
from operator import itemgetter
from Products.CMFCore.utils import getToolByName
from StringIO import StringIO
from zope.publisher.browser import BrowserView
import logging


class PloneSiteAPI(BrowserView):

    def __init__(self, *args, **kwargs):
        super(PloneSiteAPI, self).__init__(*args, **kwargs)
        self.portal_setup = getToolByName(self.context, 'portal_setup')
        self.gatherer = IUpgradeInformationGatherer(self.portal_setup)

    @jsonify
    @action('GET')
    def get_profile(self, profileid):
        """Returns a JSON-encoded dict representation of the Generic Setup
        profile with the given ``id``.
        """
        return self._refine_profile_info(self._get_profile_info(profileid))

    @jsonify
    @action('GET')
    def list_profiles(self):
        """Returns a list of all installed profiles and their upgrade steps.
        """
        return map(self._refine_profile_info, self.gatherer.get_profiles())

    @jsonify
    @action('GET')
    def list_profiles_proposing_upgrades(self):
        """Returns a list of profiles with proposed upgrade steps, only
        containing the proposed upgrade steps for each profile.
        """
        return map(self._refine_profile_info,
                   self._get_profiles_proposing_upgrades())

    @jsonify
    @action('GET')
    def list_proposed_upgrades(self):
        """Returns a list of proposed upgrades.
        """
        return map(self._refine_upgrade_info, self._get_proposed_upgrades())

    @action('POST', rename_params={'upgrades': 'upgrades:list'})
    def execute_upgrades(self, upgrades):
        """Execute a list of upgrades, each identified by the upgrade ID
        returned by the profile listing actions
        (``[dest-version]@[profile ID]``).
        """
        self._require_up_to_date_plone_site()
        upgrade_infos = self.gatherer.get_upgrades_by_api_ids(*upgrades)
        return self._install_upgrades(upgrade_infos)

    @action('POST')
    def execute_proposed_upgrades(self):
        """Execute all proposed upgrades on this Plone site.
        """
        self._require_up_to_date_plone_site()
        upgrades = reduce(list.__add__,
                          map(itemgetter('upgrades'),
                              self._get_profiles_proposing_upgrades()))
        return self._install_upgrades(upgrades)

    def _refine_profile_info(self, profile):
        return {'id': profile['id'],
                'title': profile['title'],
                'product': profile['product'],
                'db_version': profile['db_version'],
                'fs_version': profile['version'],
                'outdated_fs_version': False,
                'upgrades': map(self._refine_upgrade_info, profile['upgrades'])}

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
            return {}
        else:
            return profiles[0]

    def _get_profiles_proposing_upgrades(self):
        profiles = map(self._filter_proposed_upgrades_in_profile,
                       self.gatherer.get_profiles())
        return filter(itemgetter('upgrades'), profiles)

    def _get_proposed_upgrades(self):
        return reduce(list.__add__,
                      map(itemgetter('upgrades'),
                          self._get_profiles_proposing_upgrades()))

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
