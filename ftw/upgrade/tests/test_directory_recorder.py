from ftw.upgrade.interfaces import IUpgradeStepRecorder
from ftw.upgrade.testing import FTW_UPGRADE_INTEGRATION_TESTING
from unittest2 import TestCase
from zope.component import getMultiAdapter


PROFILE_NAME = 'ftw.upgrade.tests.directory_upgrades:default'


class TestUpgradeStepRecorder(TestCase):
    layer = FTW_UPGRADE_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer['portal']
        self.recorder = getMultiAdapter((self.portal, PROFILE_NAME),
                                        IUpgradeStepRecorder)

    def test_marking_upgrades_as_installed(self):
        self.assertFalse(self.recorder.is_installed('20140101083000'))
        self.recorder.mark_as_installed('20140101083000')
        self.assertTrue(self.recorder.is_installed('20140101083000'))
