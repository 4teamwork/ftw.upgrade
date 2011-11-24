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

    def __init__(upgrade_class):
        """Initializes a upgrade information object for the passed upgrade
        class.

        Arguments:
        `upgrade_class` -- the upgrade class.
        """

    def get_title():
        """Returns the title, which is the dotted name of the class.
        """

    def get_description():
        """Returns the description, which is the docstring of the upgrade
        class.
        """

    def is_installed():
        """Returns `True` if the upgrade is already installed.
        """

    def get_class():
        """Returns the class of the upgrade.
        """
