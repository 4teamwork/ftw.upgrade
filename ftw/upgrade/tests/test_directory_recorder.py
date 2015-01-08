from ftw.upgrade.interfaces import IUpgradeStepRecorder
from ftw.upgrade.tests.base import UpgradeTestCase
from zope.component import getMultiAdapter


class TestUpgradeStepRecorder(UpgradeTestCase):

    def test_marking_upgrades_as_installed(self):
        recorder = getMultiAdapter((self.layer['portal'], 'some.package:default'),
                                   IUpgradeStepRecorder)

        self.assertFalse(recorder.is_installed('20140101083000'))
        recorder.mark_as_installed('20140101083000')
        self.assertTrue(recorder.is_installed('20140101083000'))
