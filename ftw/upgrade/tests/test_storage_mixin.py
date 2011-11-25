from ftw.upgrade.info import UpgradeInfo
from ftw.upgrade.interfaces import IStorageMixin
from ftw.upgrade.interfaces import IUpgradeManager
from ftw.upgrade.manager import UpgradeManager
from ftw.upgrade.mixins.storage import StorageMixin
from ftw.upgrade.testing import UPGRADE_ZCML_LAYER
from ftw.upgrade.tests.data.foo.upgrades.testupgrade import MyUpgrade
from ftw.upgrade.utils import get_dotted_name
from plone.mocktestcase import MockTestCase
from zope.app.component.hooks import setSite
from zope.component import getSiteManager
from zope.interface import alsoProvides
from zope.interface.verify import verifyClass
import zope.annotation


class TestStorageMixin(MockTestCase):

    layer = UPGRADE_ZCML_LAYER

    def setUp(self):
        super(TestStorageMixin, self).setUp()
        self.my_upgade_dotted_name = get_dotted_name(MyUpgrade)

    def _create_site(self):
        site = self.create_dummy(getSiteManager=getSiteManager)
        alsoProvides(site, zope.annotation.interfaces.IAttributeAnnotatable)
        setSite(site)

    def test_implements_interface(self):
        self.assertTrue(IStorageMixin.implementedBy(StorageMixin))
        verifyClass(IStorageMixin, StorageMixin)

    def test_is_installed_false_by_default(self):
        manager = self.mocker.mock(UpgradeManager, count=False)
        self.mock_utility(manager, IUpgradeManager)
        self.expect(
            manager.is_installed(self.my_upgade_dotted_name)).result('--')

        self._create_site()

        self.replay()

        upgrade = UpgradeInfo(MyUpgrade)
        self.assertFalse(StorageMixin().is_installed(upgrade.get_title()))

    def test_install_package(self):
        manager = self.mocker.mock(UpgradeManager, count=False)
        self.mock_utility(manager, IUpgradeManager)
        self.expect(
            manager.is_installed(self.my_upgade_dotted_name)).result('--')

        self._create_site()

        self.replay()

        upgrade = UpgradeInfo(MyUpgrade)
        self.assertFalse(StorageMixin().is_installed(upgrade.get_title()))
        StorageMixin().mark_as_installed(upgrade)
        self.assertTrue(StorageMixin().is_installed(upgrade.get_title()))

    def test_mark_as_installed_only_accepts_upgrade_infos(self):
        manager = self.mocker.mock(UpgradeManager, count=False)
        self.mock_utility(manager, IUpgradeManager)
        self.expect(
            manager.is_installed(self.my_upgade_dotted_name)).result('--')

        self.replay()

        with self.assertRaises(ValueError) as cm:
            StorageMixin().mark_as_installed(MyUpgrade)

        self.assertEqual(
            str(cm.exception),
            "Expected IUpgradeInfo object, got <class 'ftw.upgrade."
            "tests.data.foo.upgrades.testupgrade.MyUpgrade'>")
