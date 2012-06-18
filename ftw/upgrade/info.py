from ftw.upgrade.interfaces import IUpgradeInfo
from ftw.upgrade.interfaces import IUpgradeManager
from ftw.upgrade.utils import get_dotted_name
from zope.component import getUtility
from zope.interface import implements


class UpgradeInfo(object):
    """Provides information about an upgrade.
    """

    implements(IUpgradeInfo)

    def __init__(self, upgrade_class):
        """Initializes a upgrade information object for the passed upgrade
        class.

        Arguments:
        `upgrade_class` -- the upgrade class.
        """
        self._upgrade_class = upgrade_class
        dottedname = get_dotted_name(upgrade_class)

        self._title = dottedname
        self._description = upgrade_class.__doc__

        manager = getUtility(IUpgradeManager)
        self._installed = manager.is_installed(dottedname)

    def get_title(self):
        """Returns the title, which is the dotted name of the class.
        """
        return self._title

    def get_description(self):
        """Returns the description, which is the docstring of the upgrade
        class.
        """
        return self._description

    def is_installed(self):
        """Returns `True` if the upgrade is already installed.
        """
        return self._installed

    def get_class(self):
        """Returns the class of the upgrade.
        """
        return self._upgrade_class

    def get_dependencies(self):
        """Returns `IUpgradeInfo` objects of all
        """
        manager = getUtility(IUpgradeManager)
        upgrades = []
        for dottedname in self.get_class().dependencies:
            upgrades.append(manager.get_upgrade(dottedname))
        return upgrades
