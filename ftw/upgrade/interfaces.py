from zope.interface import Interface


class IUpgradeManager(Interface):
    """Utility interface for the upgrade manager.
    """

    def add_upgrade_directory(path):
        """Registers a upgrade directory.

        Arguments:
        `path` -- Absolute path of the directory.
        """
