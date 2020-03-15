from AccessControl.SecurityInfo import ClassSecurityInformation
from datetime import datetime
from ftw.upgrade.exceptions import UpgradeNotFound
from ftw.upgrade.interfaces import IRecordableHandler
from ftw.upgrade.interfaces import IUpgradeInformationGatherer
from ftw.upgrade.interfaces import IUpgradeStepRecorder
from ftw.upgrade.utils import get_sorted_profile_ids
from functools import reduce
from operator import itemgetter
from Products.CMFCore.utils import getToolByName
from Products.GenericSetup.interfaces import ISetupTool
from Products.GenericSetup.upgrade import normalize_version
from Products.GenericSetup.upgrade import UpgradeStep
from six.moves import map
from zope.component import adapts
from zope.component import getMultiAdapter
from zope.deprecation import deprecated
from zope.interface import implementer

try:
    from Products.CMFPlone.utils import get_installer
except ImportError:
    get_installer = None


def flatten_upgrades(upgrades):
    """Flattens the data structure of a list of upgrades: removes grouping.
    The result is an iterable with dicts containg upgrade information.
    """

    for item in upgrades:
        if isinstance(item, (list, tuple)):
            for subitem in flatten_upgrades(item):
                yield subitem

        else:
            yield item


def flag_profiles_with_outdated_fs_version(upgrades):
    """Flags profiles that contain an upgrade that leads to a destination
    version that is higher than that profile's current filesystem version.

    This usually means someone wrote an upgrade step, but forgot to update the
    version in metadata.xml of the corresponding profile. The upgrade step in
    question will also be flagged.
    """

    for profile in upgrades:
        profile['outdated_fs_version'] = False
        fs_version = normalize_version(profile['version'])

        for upgrade in profile['upgrades']:
            dest_version = normalize_version(upgrade['sdest'])
            upgrade['outdated_fs_version'] = dest_version > fs_version
            if upgrade['outdated_fs_version']:
                profile['outdated_fs_version'] = True

    return upgrades


def extend_auto_upgrades_with_human_formatted_date_version(profiles):
    """Adds a 'fsource' and / or 'fdest' key to each upgrade dist where the
    corresponding version is a 14 digit timestamp with the timestamp in a
    human readable format.
    """
    to_human_readable = lambda datestr: datetime.strptime(datestr, '%Y%m%d%H%M%S') \
        .strftime('%Y/%m/%d %H:%M')

    for profile in profiles:
        if len(profile.get('db_version', '')) == 14:
            try:
                profile['formatted_db_version'] = to_human_readable(
                    profile['db_version'])
            except ValueError:
                pass

        if len(profile.get('version', '')) == 14:
            try:
                profile['formatted_version'] = to_human_readable(
                    profile['version'])
            except ValueError:
                pass

        for upgrade in profile['upgrades']:
            if len(upgrade['ssource']) == 14:
                try:
                    upgrade['fsource'] = to_human_readable(upgrade['ssource'])
                except ValueError:
                    pass

            if len(upgrade['sdest']) == 14:
                try:
                    upgrade['fdest'] = to_human_readable(upgrade['sdest'])
                except ValueError:
                    pass

    return profiles


@implementer(IUpgradeInformationGatherer)
class UpgradeInformationGatherer(object):
    adapts(ISetupTool)

    security = ClassSecurityInformation()

    def __init__(self, portal_setup):
        self.portal_setup = portal_setup
        self.portal = getToolByName(
            portal_setup, 'portal_url').getPortalObject()
        self.cyclic_dependencies = False

    security.declarePrivate('get_profiles')
    def get_profiles(self, proposed_only=False, propose_deferrable=True):
        profiles = self._sort_profiles_by_dependencies(
            self._get_profiles(proposed_only=proposed_only,
                               propose_deferrable=propose_deferrable))
        profiles = flag_profiles_with_outdated_fs_version(profiles)
        profiles = extend_auto_upgrades_with_human_formatted_date_version(
            profiles)
        return profiles

    security.declarePrivate('get_upgrades')
    get_upgrades = deprecated(get_profiles,
                              'get_upgrades was renamed to get_profiles')

    security.declarePrivate('get_upgrades_by_api_ids')
    def get_upgrades_by_api_ids(self, *api_ids, **kwargs):
        propose_deferrable = kwargs.pop('propose_deferrable', True)
        upgrades = [
            upgrade for upgrade
            in reduce(list.__add__, map(itemgetter('upgrades'),
                      self.get_profiles(propose_deferrable=propose_deferrable)))
            if upgrade['api_id'] in api_ids
        ]

        missing_api_ids = (set(api_ids)
                           - set(map(itemgetter('api_id'), upgrades)))
        if missing_api_ids:
            raise UpgradeNotFound(tuple(missing_api_ids)[0])
        return upgrades

    security.declarePrivate('_get_profiles')
    def _get_profiles(self, proposed_only=False, propose_deferrable=True):
        for profileid in self.portal_setup.listProfilesWithUpgrades():
            if not self._is_profile_installed(profileid):
                continue

            data = self._get_profile_data(profileid,
                                          proposed_only=proposed_only,
                                          propose_deferrable=propose_deferrable)
            if len(data['upgrades']) == 0:
                continue

            if profileid == 'Products.CMFPlone:plone':
                # Plone has its own migration mechanism.
                # We do not support upgrading plone.
                continue

            yield data

    security.declarePrivate('_get_profile_data')
    def _get_profile_data(self, profileid,
                          proposed_only=False,
                          propose_deferrable=True):
        db_version = self.portal_setup.getLastVersionForProfile(profileid)
        if isinstance(db_version, (tuple, list)):
            db_version = '.'.join(db_version)

        data = {
            'upgrades': self._get_profile_upgrades(
                    profileid,
                    proposed_only=proposed_only,
                    propose_deferrable=propose_deferrable),
            'db_version': db_version}

        try:
            profile_info = self.portal_setup.getProfileInfo(profileid).copy()
            if 'for' in profile_info:
                del profile_info['for']
            data.update(profile_info)

        except KeyError as exc:
            if exc.args and exc.args[0] == profileid:
                # package was removed - profile is no longer available.
                return {'upgrades': []}

            else:
                raise

        return data

    security.declarePrivate('_get_profile_upgrades')
    def _get_profile_upgrades(self, profileid,
                              proposed_only=False,
                              propose_deferrable=True):
        proposed_ids = set()
        upgrades = []

        proposed_upgrades = list(flatten_upgrades(
                self.portal_setup.listUpgrades(profileid)))
        all_upgrades = list(flatten_upgrades(
                self.portal_setup.listUpgrades(profileid, show_old=True)))

        for upgrade in proposed_upgrades:
            proposed_ids.add(upgrade['id'])

        for upgrade in all_upgrades:
            upgrade = upgrade.copy()
            if upgrade['id'] not in proposed_ids:
                upgrade['proposed'] = False
                upgrade['done'] = True

            if self._was_upgrade_executed(profileid, upgrade):
                upgrade['proposed'] = False
                upgrade['done'] = True

            upgrade['orphan'] = self._is_orphan(profileid, upgrade)
            if upgrade['orphan']:
                upgrade['proposed'] = True
                upgrade['done'] = False

            upgrade['deferrable'] = self._is_deferrable(upgrade)
            if upgrade['deferrable'] and upgrade['proposed']:
                upgrade['proposed'] = propose_deferrable

            if 'step' in upgrade:
                del upgrade['step']

            upgrade['profile'] = profileid
            upgrade['api_id'] = '@'.join((upgrade['sdest'], profileid))

            if proposed_only and not upgrade['proposed']:
                continue

            upgrades.append(upgrade)

        return upgrades

    security.declarePrivate('_is_profile_installed')
    def _is_profile_installed(self, profileid):
        try:
            profileinfo = self.portal_setup.getProfileInfo(profileid)
        except KeyError:
            return False
        product = profileinfo['product']

        if get_installer is not None:
            quickinstaller = get_installer(self.portal, self.portal.REQUEST)

            if (quickinstaller.is_product_installable(product)
                    and not quickinstaller.is_product_installed(product)):
                return False
        else:
            quickinstaller = getToolByName(
                self.portal_setup, 'portal_quickinstaller')
            if (quickinstaller.isProductInstallable(product)
                    and not quickinstaller.isProductInstalled(product)):
                return False

        version = self.portal_setup.getLastVersionForProfile(profileid)
        return version != 'unknown'

    security.declarePrivate('_sort_profiles_by_dependencies')
    def _sort_profiles_by_dependencies(self, profiles):
        """Sort the profiles so that the profiles are listed after its
        dependencies since it is safer to first install dependencies.
        """

        sorted_profile_ids = get_sorted_profile_ids(self.portal_setup)
        return sorted(profiles,
                      key=lambda p: sorted_profile_ids.index(p.get('id')))

    security.declarePrivate('_is_orphan')
    def _is_orphan(self, profile, upgrade_step_info):
        if upgrade_step_info['proposed']:
            return False
        if not self._is_recordeable(upgrade_step_info):
            return False
        return not self._was_upgrade_executed(profile, upgrade_step_info)

    security.declarePrivate('_is_deferrable')
    def _is_deferrable(self, upgrade_step_info):
        step = upgrade_step_info.get('step')
        if not step:
            return False

        maybe_ftw_upgrade_step_wrapper = getattr(step, 'handler', None)
        if not maybe_ftw_upgrade_step_wrapper:
            return False

        upgrade_step_class = getattr(
            maybe_ftw_upgrade_step_wrapper, 'handler', None)
        if not upgrade_step_class:
            return False

        return bool(getattr(upgrade_step_class, 'deferrable', False))

    security.declarePrivate('_is_recordeable')
    def _is_recordeable(self, upgrade_step_info):
        if not isinstance(upgrade_step_info['step'], UpgradeStep):
            return False
        handler = upgrade_step_info['step'].handler
        return IRecordableHandler.providedBy(handler)

    security.declarePrivate('_was_upgrade_executed')
    def _was_upgrade_executed(self, profile, upgrade_step_info):
        """Check for whether we know if an upgrade step was executed.

        Returns True when the recorder is sure that this upgrade was executed.
        Returns False when the recorder is sure that it was not executed.
        Returns None when the recorder does not know whether this upgrade was executed.
        """
        if not self._is_recordeable(upgrade_step_info):
            return None
        else:
            recorder = getMultiAdapter((self.portal, profile),
                                       IUpgradeStepRecorder)
            return recorder.is_installed(upgrade_step_info['sdest'])
