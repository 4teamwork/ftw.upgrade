from ftw.upgrade.info import UpgradeInfo
from ftw.upgrade.interfaces import IUpgradeManager
from ftw.upgrade.mixins.catalog import CatalogMixin
from ftw.upgrade.mixins.storage import StorageMixin
from ftw.upgrade.utils import order_upgrades, discover_upgrades
from types import ModuleType
from zope.interface import implements


class UpgradeManager(CatalogMixin, StorageMixin):
    implements(IUpgradeManager)

    def __init__(self):
        CatalogMixin.__init__(self)
        StorageMixin.__init__(self)
        self._upgrade_packages = []
        self._upgrades = None

    def add_upgrade_package(self, module):
        if not isinstance(module, ModuleType):
            raise ValueError('Expected module, got "%s"' % str(module))

        self._upgrade_packages.append(module)

    def list_upgrades(self):
        self._load()
        return self._upgrades.values()

    def install_upgrades(self, upgrades):
        ordered = order_upgrades(upgrades)
        for upgrade in ordered:
            upgrade()()
        self.finish_catalog_tasks()

    def get_upgrade(self, dottedname):
        self._load()
        return self._upgrades[dottedname]

    def _load(self):
        if self._upgrades is not None:
            return
        self._upgrades = {}
        for package in self._upgrade_packages:
            self._load_package(package)

    def _load_package(self, package):
        for cls in discover_upgrades(package):
            info = UpgradeInfo(cls)
            self._upgrades[info.get_title()] = info
