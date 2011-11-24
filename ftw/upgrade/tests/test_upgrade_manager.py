from ftw.upgrade.interfaces import IUpgradeManager
from ftw.upgrade.manager import UpgradeManager
from ftw.upgrade.testing import UPGRADE_ZCML_LAYER
from plone.mocktestcase import MockTestCase
from zope.component import getUtility
from zope.interface.verify import verifyClass
import os.path


class TestUpgradeManager(MockTestCase):

    layer = UPGRADE_ZCML_LAYER

    def test_implements_interface(self):
        self.assertTrue(IUpgradeManager.implementedBy(UpgradeManager))
        verifyClass(IUpgradeManager, UpgradeManager)

    def test_registered_as_utility(self):
        manager = getUtility(IUpgradeManager)
        self.assertEqual(manager.__class__, UpgradeManager)
        self.assertEqual(getUtility(IUpgradeManager), manager)

    def test_add_upgrade_directory_raises_with_relative_path(self):
        manager = UpgradeManager()

        with self.assertRaises(ValueError) as cm:
            manager.add_upgrade_directory('foo/bar')

        self.assertEqual(
            str(cm.exception),
            '`path` should be absolute, got "foo/bar".')

    def test_add_upgrade_directory_works_with_absolute_path(self):
        manager = UpgradeManager()
        path = os.path.abspath(os.path.dirname(__file__))
        manager.add_upgrade_directory(path)
        self.assertEqual(manager._upgrade_directories, [path])

    def test_add_upgrade_directory_fails_when_directory_does_not_exist(self):
        manager = UpgradeManager()
        path = '/not/existing/path'
        self.assertFalse(os.path.exists(path))  # we need a wrong path

        with self.assertRaises(ValueError) as cm:
            manager.add_upgrade_directory(path)

        self.assertEqual(
            str(cm.exception),
            'Upgrade directory path does not exist (%s).' % path)

    def test_add_upgrade_directory_fails_if_path_is_not_a_directory(self):
        manager = UpgradeManager()
        path = __file__

        with self.assertRaises(ValueError) as cm:
            manager.add_upgrade_directory(path)

        self.assertEqual(
            str(cm.exception),
            'Upgrades: path is not a directory (%s).' % path)
