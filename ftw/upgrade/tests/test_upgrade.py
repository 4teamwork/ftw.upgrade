from plone.mocktestcase import MockTestCase
from ftw.upgrade.upgrade import BaseUpgrade
from ftw.upgrade.interfaces import IUpgradeManager
from zope.component import getUtility
from ftw.upgrade.testing import UPGRADE_ZCML_LAYER


class TestUpgrade(MockTestCase):
    
    layer = UPGRADE_ZCML_LAYER
    
    def test_upgrade(self):
        myUpgrade = BaseUpgrade()
        manager = getUtility(IUpgradeManager)
        self.assertEqual(myUpgrade.manager, manager)
        with self.assertRaises(NotImplementedError) as cm:
            myUpgrade()
        self.assertEqual(
            str(cm.exception),
            'You have to implement the __call__ method to create an Upgrade')