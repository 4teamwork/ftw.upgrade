from AccessControl.SecurityInfo import ClassSecurityInformation
from ftw.upgrade.interfaces import IUpgradeInformationGatherer
from ftw.upgrade.utils import get_sorted_profile_ids
from Products.GenericSetup.interfaces import ISetupTool
from Products.GenericSetup.upgrade import normalize_version
from zope.component import adapts
from zope.interface import implements


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


class UpgradeInformationGatherer(object):
    implements(IUpgradeInformationGatherer)
    adapts(ISetupTool)

    security = ClassSecurityInformation()

    def __init__(self, portal_setup):
        self.portal_setup = portal_setup
        self.cyclic_dependencies = False

    security.declarePrivate('get_upgrades')
    def get_upgrades(self):
        profiles = self._sort_profiles_by_dependencies(self._get_profiles())
        profiles = flag_profiles_with_outdated_fs_version(profiles)
        return profiles

    security.declarePrivate('_get_profiles')
    def _get_profiles(self):
        for profileid in self.portal_setup.listProfilesWithUpgrades():
            if not self._is_profile_installed(profileid):
                continue

            data = self._get_profile_data(profileid)
            if len(data['upgrades']) == 0:
                continue

            if profileid == 'Products.CMFPlone:plone':
                # Plone has its own migration mechanism.
                # We do not support upgrading plone.
                continue

            yield data

    security.declarePrivate('_get_profile_data')
    def _get_profile_data(self, profileid):
        db_version = self.portal_setup.getLastVersionForProfile(profileid)
        if isinstance(db_version, (tuple, list)):
            db_version = '.'.join(db_version)

        data = {'upgrades': self._get_profile_upgrades(profileid),
                'db_version': db_version}

        try:
            profile_info = self.portal_setup.getProfileInfo(profileid).copy()
            if 'for' in profile_info:
                del profile_info['for']
            data.update(profile_info)

        except KeyError, exc:
            if exc.args and exc.args[0] == profileid:
                # package was removed - profile is no longer available.
                return {'upgrades': []}

            else:
                raise

        return data

    security.declarePrivate('_get_profile_upgrades')
    def _get_profile_upgrades(self, profileid):
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
            if 'step' in upgrade:
                del upgrade['step']

            if upgrade['id'] not in proposed_ids:
                upgrade['proposed'] = False
                upgrade['done'] = True

            upgrades.append(upgrade)

        return upgrades

    security.declarePrivate('_is_profile_installed')
    def _is_profile_installed(self, profileid):
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
