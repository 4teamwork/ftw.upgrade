# pylint: disable=E0211, E0213
# E0211: Method has no argument
# E0213: Method should have "self" as first argument

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

    def is_installed(dottedname):
        """Returns `True` if the class with the dottedname is installed.

        Arguments:
        `dottedname` -- dotted name of the upgrade class.
        """


class IUpgradeInfo(Interface):
    """Provides information about an upgrade.
    """
