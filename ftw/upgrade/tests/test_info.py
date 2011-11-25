from ftw.upgrade.info import UpgradeInfo
from ftw.upgrade.interfaces import IUpgradeInfo
from ftw.upgrade.interfaces import IUpgradeManager
from ftw.upgrade.manager import UpgradeManager
from mocker import Mocker, expect
from unittest2 import TestCase
from zope.component import provideUtility
from zope.interface.verify import verifyClass


class MyUpgrade(object):
    """This fake upgrade does nothing.
    """


class NotInstalled(object):
    """This upgrade is not installed.
    """


class AnotherUpgrade(object):
    """An upgrade
    """

    dependencies = ['ftw.upgrade.tests.test_info.MyUpgrade']


class TestUpgradeInfo(TestCase):

    def setUp(self):
        self.testcase_mocker = Mocker()
        manager = self.testcase_mocker.mock(UpgradeManager, count=False)
        provideUtility(component=manager, provides=IUpgradeManager)

        expect(manager.is_installed(
                'ftw.upgrade.tests.test_info.MyUpgrade')).result(True)

        expect(manager.is_installed(
                'ftw.upgrade.tests.test_info.NotInstalled')).result(False)

        expect(manager.is_installed(
                'ftw.upgrade.tests.test_info.AnotherUpgrade')).result(False)

        self.myupgrade_info = UpgradeInfo(MyUpgrade)
        expect(manager.get_upgrade(
                'ftw.upgrade.tests.test_info.MyUpgrade')).result(
            self.myupgrade_info)

        self.testcase_mocker.replay()

    def tearDown(self):
        self.testcase_mocker.verify()
        self.testcase_mocker.restore()

    def test_implements_interface(self):
        self.assertTrue(IUpgradeInfo.implementedBy(UpgradeInfo))
        verifyClass(IUpgradeInfo, UpgradeInfo)

    def test_get_title(self):
        self.assertEqual(UpgradeInfo(MyUpgrade).get_title(),
                         'ftw.upgrade.tests.test_info.MyUpgrade')

    def test_get_description(self):
        info = UpgradeInfo(MyUpgrade)
        self.assertEqual(info.get_description().strip(),
                         'This fake upgrade does nothing.')

    def test_is_installed(self):
        self.assertEqual(UpgradeInfo(MyUpgrade).is_installed(),
                         True)

        self.assertEqual(UpgradeInfo(NotInstalled).is_installed(),
                         False)

    def test_get_class(self):
        self.assertEqual(UpgradeInfo(MyUpgrade).get_class(), MyUpgrade)

    def test_get_dependencies(self):
        another = UpgradeInfo(AnotherUpgrade)
        self.assertEqual(another.get_dependencies(), [self.myupgrade_info])
