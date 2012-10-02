from Products.GenericSetup.interfaces import ISetupTool
from ftw.upgrade.exceptions import CyclicDependencies
from ftw.upgrade.interfaces import IUpgradeInformationGatherer
from ftw.upgrade.utils import topological_sort
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


class UpgradeInformationGatherer(object):
    implements(IUpgradeInformationGatherer)
    adapts(ISetupTool)

    def __init__(self, portal_setup):
        self.portal_setup = portal_setup
        self.cyclic_dependencies = False

    def get_upgrades(self):
        return self._sort_profiles_by_dependencies(self._get_profiles())

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

    def _get_profile_data(self, profileid):
        db_version = self.portal_setup.getLastVersionForProfile(profileid)
        if isinstance(db_version, (tuple, list)):
            db_version = '.'.join(db_version)

        data = {'upgrades': self._get_profile_upgrades(profileid),
                'db_version': db_version}

        try:
            data.update(self.portal_setup.getProfileInfo(profileid))
        except KeyError, exc:
            if exc.args and exc.args[0] == profileid:
                # package was removed - profile is no longer available.
                return {'upgrades': []}
            else:
                raise

        return data

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

            if upgrade['id'] not in proposed_ids:
                upgrade['proposed'] = False
                upgrade['done'] = True

            upgrades.append(upgrade)

        return upgrades

    def _is_profile_installed(self, profileid):
        version = self.portal_setup.getLastVersionForProfile(profileid)
        return version != 'unknown'

    def _sort_profiles_by_dependencies(self, profiles):
        """Sort the profiles so that the profiles are listed after its
        dependencies since it is safer to first install dependencies.
        """
        profile_ids = []
        dependencies = []

        for profile in self.portal_setup.listProfileInfo():
            profile_ids.append(profile['id'])

        for profile in self.portal_setup.listProfileInfo():
            if not profile.get('dependencies'):
                continue

            for dependency in profile.get('dependencies'):
                if dependency.startswith('profile-'):
                    dependency = dependency.split('profile-', 1)[1]
                else:
                    continue

                if dependency not in profile_ids:
                    continue
                dependencies.append((profile['id'], dependency))

        order = topological_sort(profile_ids, dependencies)
        if order is None:
            # cyclic
            profiles = sorted(profiles, key=lambda p: p.get('id'))
            raise CyclicDependencies(profiles)

        else:
            order = list(reversed(order))
            return sorted(profiles, key=lambda p: order.index(p.get('id')))
