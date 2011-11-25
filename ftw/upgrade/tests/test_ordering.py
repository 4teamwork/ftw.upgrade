# pylint: disable=W0212, W0201
# W0212: Access to a protected member of a client class
# W0201: Attribute defined outside __init__

from ftw.upgrade import utils
from ftw.upgrade.interfaces import IUpgradeManager
from ftw.upgrade.testing import UPGRADE_ZCML_LAYER
from ftw.upgrade.tests.data import foo
from plone.mocktestcase import MockTestCase
from zope.component import getUtility


class TestOrdering(MockTestCase):

    layer = UPGRADE_ZCML_LAYER

    def test_order_upgrades(self):
        manager = getUtility(IUpgradeManager)

        manager.add_upgrade_package(foo.upgrades)
        manager.list_upgrades()

        upgrades = manager._upgrades
        del(upgrades['ftw.upgrade.tests.data.foo.'
                     'upgrades.testupgrade.MyUpgrade'])

        ordered_upgrades = utils.order_upgrades(upgrades.values())
        ordered_upgrades_titles = []
        for upgrade in ordered_upgrades:
            ordered_upgrades_titles.append(upgrade.get_title())

        prefix = 'ftw.upgrade.tests.data.foo.upgrades.testupgrade.'
        expected_upgrades = [
            upgrades[prefix + 'MyUpgrade3'].get_title(),
            upgrades[prefix + 'MyUpgrade4'].get_title(),
            upgrades[prefix + 'MyUpgrade2'].get_title(),
            upgrades[prefix + 'MyUpgrade1'].get_title(),
            upgrades[prefix + 'MyUpgrade5'].get_title(),
        ]
        self.assertEqual(ordered_upgrades_titles, expected_upgrades)
