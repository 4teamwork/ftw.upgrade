from ftw.upgrade.exceptions import CircularUpgradeDependencies
from ftw.upgrade.info import UpgradeInfo
from ftw.upgrade.tests.data.foo.upgrades import testupgrade
from unittest import TestCase


class TestCircularUpgradeDependencies(TestCase):

    def test_list_of_strings(self):
        exc = CircularUpgradeDependencies(['foo', 'bar'])
        self.assertEqual(str(exc), 'foo -> bar -> foo')

    def test_list_of_one_string(self):
        exc = CircularUpgradeDependencies(['foo'])
        self.assertEqual(str(exc), 'foo -> foo')

    def test_fallback_on_unkown_types(self):
        self.assertEqual(str(CircularUpgradeDependencies('foo')), 'foo')
        self.assertEqual(str(CircularUpgradeDependencies(None)), 'None')
        self.assertEqual(str(CircularUpgradeDependencies(True)), 'True')
        self.assertEqual(str(CircularUpgradeDependencies(False)), 'False')
        self.assertEqual(str(CircularUpgradeDependencies(3)), '3')

    def test_upgrade_info_objects_use_titles(self):
        upgrades = [UpgradeInfo(testupgrade.MyUpgrade1),
                    UpgradeInfo(testupgrade.MyUpgrade3)]

        msg = str(CircularUpgradeDependencies(upgrades))

        self.assertEqual(msg, ' -> '.join((
                    '%sMyUpgrade1' % testupgrade.PREFIX,
                    '%sMyUpgrade3' % testupgrade.PREFIX,
                    '%sMyUpgrade1' % testupgrade.PREFIX)))
