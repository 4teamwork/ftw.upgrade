from ftw.upgrade.testing import INTID_UPGRADE_FUNCTIONAL_TESTING
from ftw.upgrade.tests import test_upgrade_step


class TestUpgradeStepIntids(test_upgrade_step.TestUpgradeStep):

    layer = INTID_UPGRADE_FUNCTIONAL_TESTING
