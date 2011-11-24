from zope.interface import Interface


class IUpgradeManager(Interface):
    """Utility interface for the upgrade manager.
    """

    def add_upgrade_directory(path):
        """Registers a upgrade directory.

        Arguments:
        `path` -- Absolute path of the directory.
        """

    def list_upgrades():
        """Returns all upgrades represented as `IUpgradeInfo' objects.
        """

    def install_upgrades(upgrades):
        """Installs a list of upgrades.

        Arguments:
        `upgrades` -- A list of `IUpgradeInfo` objects.
        """


class IUpgradeInfo(Interface):
    """Provides information about an upgrade.
    """
