from ftw.upgrade.info import UpgradeInfo
from ftw.upgrade.interfaces import IUpgradeInfo
from ftw.upgrade.interfaces import IUpgradeManager
from plone.mocktestcase import MockTestCase
from zope.interface.verify import verifyClass


class MyUpgrade(object):
    """This fake upgrade does nothing.
    """


class TestUpgradeInfo(TestCase):

    def test_implements_interface(self):
        self.assertTrue(IUpgradeInfo.implementedBy(UpgradeInfo))
        verifyClass(IUpgradeInfo, UpgradeInfo)

    def test_get_title(self):
        info = UpgradeInfo(MyUpgrade)
        self.assertEqual(info.get_title(),
                         'ftw.upgrade.tests.test_info.MyUpgrade')

    def test_get_description(self):
        info = UpgradeInfo(MyUpgrade)
        self.assertEqual(info.get_description(),
                         'This fake upgrade does nothing.')

    def test_is_installed(self):
        pass
