from ftw.upgrade.testing import UPGRADE_ZCML_LAYER
from plone.mocktestcase import MockTestCase
from plone.testing import zca
from zope.configuration import xmlconfig
import ftw.upgrade.tests.data.foo
from ftw.upgrade.manager import UpgradeManager
from ftw.upgrade import utils
from ftw.upgrade.interfaces import IUpgradeManager
from zope.component import getUtility


class TestOrdering(MockTestCase):

    layer = UPGRADE_ZCML_LAYER


    def test_order_upgrades(self):
        manager = getUtility(IUpgradeManager)
        import ftw.upgrade.tests.data.foo.upgrades
        manager.add_upgrade_package(ftw.upgrade.tests.data.foo.upgrades)
        manager.list_upgrades()
        # with self.assertRaises(ValueError) as cm: 
        #     orderedupgrades = utils.order_upgrades(manager._upgrades)
        # self.assertEqual(
        #     str(cm.exception),
        #     'Some of your upgrades got Circular Dependencies. \
        #     Can not upgrade that way')
        upgrades = manager._upgrades
        del(upgrades['ftw.upgrade.tests.data.foo.upgrades.testupgrade.MyUpgrade'])
        
        # del(upgrades['ftw.upgrade.tests.data.foo.upgrades.testupgrade.MyUpgrade6'])
        # del(upgrades['ftw.upgrade.tests.data.foo.upgrades.testupgrade.MyUpgrade7'])
        # del(upgrades['ftw.upgrade.tests.data.foo.upgrades.testupgrade.MyUpgrade8'])
        ordered_upgrades = utils.order_upgrades(upgrades.values())
        ordered_upgrades_titles = []
        for upgrade in ordered_upgrades: ordered_upgrades_titles.append(upgrade.get_title())
        expected_upgrades = [
            upgrades['ftw.upgrade.tests.data.foo.upgrades.testupgrade.MyUpgrade3'].get_title(),
            upgrades['ftw.upgrade.tests.data.foo.upgrades.testupgrade.MyUpgrade4'].get_title(),
            upgrades['ftw.upgrade.tests.data.foo.upgrades.testupgrade.MyUpgrade2'].get_title(),
            upgrades['ftw.upgrade.tests.data.foo.upgrades.testupgrade.MyUpgrade1'].get_title(),
            upgrades['ftw.upgrade.tests.data.foo.upgrades.testupgrade.MyUpgrade5'].get_title(),
        ]
        self.assertEqual(ordered_upgrades_titles, expected_upgrades)
