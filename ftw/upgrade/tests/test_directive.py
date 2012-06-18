from ftw.upgrade.interfaces import IUpgradeManager
from ftw.upgrade.manager import UpgradeManager
from ftw.upgrade.testing import UPGRADE_ZCML_LAYER
from ftw.testing import MockTestCase
from plone.testing import zca
from zope.configuration import xmlconfig
import ftw.upgrade.tests.data.foo


class TestDirective(MockTestCase):

    layer = UPGRADE_ZCML_LAYER

    def setUp(self):
        super(TestDirective, self).setUp()
        self.configurationContext = zca.stackConfigurationContext(
            self.layer.get('configurationContext'))

        xmlconfig.file('configure.zcml', ftw.upgrade,
                       context=self.configurationContext)

    def tearDown(self):
        super(TestDirective, self).tearDown()
        self.configurationContext = None

    def test_directive(self):
        manager = self.mocker.mock(UpgradeManager)
        self.mock_utility(manager, IUpgradeManager)
        manager.add_upgrade_package(ftw.upgrade.tests.data.foo.upgrades)
        self.replay()
        xmlconfig.file('configure.zcml', ftw.upgrade.tests.data.foo,
                       context=self.configurationContext)
