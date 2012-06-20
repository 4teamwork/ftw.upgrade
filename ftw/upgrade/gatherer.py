from Products.GenericSetup.interfaces import ISetupTool
from ftw.upgrade.interfaces import IUpgradeInformationGatherer
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

    def get_upgrades(self):
        return sorted(self._get_profiles(),
                      key=lambda item: item.get('product'))

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
        data.update(self.portal_setup.getProfileInfo(profileid))
        return data

    def _get_profile_upgrades(self, profileid):
        proposed_ids = set()
        upgrades = []

        for upgrade in flatten_upgrades(
            self.portal_setup.listUpgrades(profileid)):
            upgrade = upgrade.copy()
            upgrades.append(upgrade)
            proposed_ids.add(upgrade['id'])

        for upgrade in flatten_upgrades(
            self.portal_setup.listUpgrades(profileid, show_old=True)):
            if upgrade['id'] in proposed_ids:
                continue

            upgrade = upgrade.copy()
            upgrade['proposed'] = False
            upgrade['done'] = True
            upgrades.append(upgrade)

        return upgrades

    def _is_profile_installed(self, profileid):
        version = self.portal_setup.getLastVersionForProfile(profileid)
        return version != 'unknown'
