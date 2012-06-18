# pylint: disable=W0212, W0201
# W0212: Access to a protected member of a client class
# W0201: Attribute defined outside __init__

from ftw.upgrade.interfaces import ICatalogMixin
from ftw.upgrade.interfaces import IStorageMixin
from ftw.upgrade.interfaces import IUpgradeManager
from ftw.upgrade.manager import UpgradeManager
from ftw.upgrade.testing import UPGRADE_ZCML_LAYER
from ftw.upgrade.tests.data import bar
from ftw.upgrade.tests.data import foo
from ftw.testing import MockTestCase
from zope.component import getUtility
from zope.interface.verify import verifyClass


class TestUpgradeManager(MockTestCase):

    layer = UPGRADE_ZCML_LAYER

    def test_implements_interface(self):
        self.assertTrue(IUpgradeManager.implementedBy(UpgradeManager))
        verifyClass(IUpgradeManager, UpgradeManager)

    def test_has_catalog_mixin(self):
        self.assertTrue(ICatalogMixin.implementedBy(UpgradeManager))
        verifyClass(ICatalogMixin, UpgradeManager)

    def test_has_storage_mixin(self):
        self.assertTrue(IStorageMixin.implementedBy(UpgradeManager))
        verifyClass(IStorageMixin, UpgradeManager)

    def test_registered_as_utility(self):
        manager = getUtility(IUpgradeManager)
        self.assertEqual(manager.__class__, UpgradeManager)
        self.assertEqual(getUtility(IUpgradeManager), manager)

    def test_add_upgrade_package_raises_if_not_module(self):
        manager = UpgradeManager()

        with self.assertRaises(ValueError) as cm:
            manager.add_upgrade_package('foo')

        self.assertEqual(
            str(cm.exception),
            'Expected module, got "foo"')

    def test_add_upgrade_package_works_with_module(self):
        manager = UpgradeManager()
        manager.add_upgrade_package(bar)
        self.assertIn(bar, manager._upgrade_packages)

    def test_list_upgrades(self):
        manager = UpgradeManager()
        manager.add_upgrade_package(foo.upgrades)
        upgrades = manager.list_upgrades()
        self.assertEqual(upgrades, manager._upgrades.values())
