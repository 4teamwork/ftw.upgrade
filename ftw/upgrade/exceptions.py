from ftw.upgrade.interfaces import IUpgradeInfo


class CircularUpgradeDependencies(Exception):

    def __init__(self, upgrade_infos):
        msg = self._prepare_message(upgrade_infos)
        super(CircularUpgradeDependencies, self).__init__(msg)

    def _prepare_message(self, upgrade_infos):
        if not isinstance(upgrade_infos, (list, tuple, set)) or \
                len(upgrade_infos) < 1:
            return str(upgrade_infos)

        # show circulation by adding first element to the end
        upgrade_infos.append(upgrade_infos[0])

        upgrades = []
        for obj in upgrade_infos:
            if IUpgradeInfo.providedBy(obj):
                upgrades.append(obj.get_title())

            else:
                upgrades.append(str(obj))

        return ' -> '.join(upgrades)
