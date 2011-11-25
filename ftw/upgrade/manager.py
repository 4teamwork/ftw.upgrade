from ftw.upgrade.info import UpgradeInfo
from ftw.upgrade.interfaces import IUpgrade
from ftw.upgrade.interfaces import IUpgradeManager
from ftw.upgrade.mixins.catalog import CatalogMixin
from ftw.upgrade.mixins.storage import StorageMixin
from ftw.upgrade.upgrade import BaseUpgrade
from ftw.upgrade.utils import get_modules, order_upgrades
from types import ModuleType
from zope.interface import implements
import inspect


class UpgradeManager(CatalogMixin, StorageMixin):
    implements(IUpgradeManager)

    def __init__(self):
        CatalogMixin.__init__(self)
        self._upgrade_packages = []
        self._upgrades = None
        self._modules = []


    def add_upgrade_package(self, module):
        if not isinstance(module, ModuleType):
            raise ValueError('Expected module, got "%s"' % str(module))

        self._upgrade_packages.append(module)

    def list_upgrades(self):
        self._load()
        return self._upgrades

    def install_upgrades(self, upgrades):
        ordered = order_upgrades(upgrades)
        for upgrade in ordered:
            upgrade()()
        self.finish_catalog_tasks()

    def get_upgrade(self, dottedname):
        self._load()
        return self._upgrades[dottedname]

    def _load(self):
        if self._upgrades != None:
            return
        self._upgrades = {}
        for package in self._upgrade_packages:
            self._modules.append(self._load_package(package))

    def _load_package(self, package):
        for module in get_modules(package):
            self._load_module(module)

    def _load_module(self, module):
        for name, obj in inspect.getmembers(module):
            if inspect.isclass(obj) and not BaseUpgrade.__call__ == obj.__call__:
                if IUpgrade.implementedBy(obj):
                    info = UpgradeInfo(obj)
                    self._upgrades[info._title]= info
