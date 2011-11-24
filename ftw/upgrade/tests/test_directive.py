from plone.mocktestcase import MockTestCase
from plone.testing import zca
from zope.configuration import xmlconfig
import ftw.upgrade.tests.data.foo
import os
from ftw.upgrade.manager import UpgradeManager
from ftw.upgrade.interfaces import IUpgradeManager
from ftw.upgrade.testing import UPGRADE_ZCML_LAYER


class TestDirective(MockTestCase):

    layer = UPGRADE_ZCML_LAYER

    def setUp(self):
        self.configurationContext = zca.stackConfigurationContext(
            self.layer.get('configurationContext'))

        xmlconfig.file('configure.zcml', ftw.upgrade,
                       context=self.configurationContext)

    def tearDown(self):
        self.configurationContext = None

    def test_directive(self):

        manager = self.mocker.mock(UpgradeManager)
        self.mock_utility(manager, IUpgradeManager)
        expected_path = os.path.abspath(os.path.join(
            os.path.dirname(__file__), 'data', 'foo', 'upgrades'))
        self.expect(manager.add_upgrade_directory(expected_path))
        self.replay()
        xmlconfig.file('configure.zcml', ftw.upgrade.tests.data.foo,
                       context=self.configurationContext)
