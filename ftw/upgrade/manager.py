from ftw.upgrade.interfaces import IUpgradeManager
from zope.interface import implements
import os.path


class UpgradeManager(object):
    implements(IUpgradeManager)

    def __init__(self):
        self._upgrade_directories = []

    def add_upgrade_directory(self, path):
        if not os.path.isabs(path):
            raise ValueError('`path` should be absolute, got "%s".' % path)

        if not os.path.exists(path):
            raise ValueError(
                'Upgrade directory path does not exist (%s).' % path)

        if not os.path.isdir(path):
            raise ValueError(
                'Upgrades: path is not a directory (%s).' % path)

        self._upgrade_directories.append(path)

    def list_upgrades(self):
        raise NotImplementedError()

    def install_upgrades(self, upgrades):
        raise NotImplementedError()
