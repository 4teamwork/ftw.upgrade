from ftw.upgrade.interfaces import IUpgrade
from ftw.upgrade.interfaces import IUpgradeManager
from ftw.upgrade.testing import UPGRADE_ZCML_LAYER
from ftw.upgrade.upgrade import BaseUpgrade
from ftw.testing import MockTestCase
from zope.component import getUtility
from zope.interface.verify import verifyClass


class TestUpgrade(MockTestCase):

    layer = UPGRADE_ZCML_LAYER

    def test_implements_interface(self):
        self.assertTrue(IUpgrade.implementedBy(BaseUpgrade))
        verifyClass(IUpgrade, BaseUpgrade)

    def test_base_upgrade_raises_not_implemented(self):
        myUpgrade = BaseUpgrade()
        with self.assertRaises(NotImplementedError) as cm:
            myUpgrade()
        self.assertEqual(
            str(cm.exception),
            'You have to implement the __call__ method to create an Upgrade')

    def test_manager_available(self):
        myUpgrade = BaseUpgrade()
        manager = getUtility(IUpgradeManager)
        self.assertEqual(myUpgrade.manager, manager)

    def test_dependencies_are_empty_in_base_upgrade(self):
        myUpgrade = BaseUpgrade()
        self.assertEqual(myUpgrade.dependencies, [])
