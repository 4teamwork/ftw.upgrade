from ftw.upgrade.tests.base import CommandAndInstanceTestCase
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.factory import _DEFAULT_PROFILE

import transaction


class TestPloneUpgradeNeededCommand(CommandAndInstanceTestCase):

    def setUp(self):
        super(TestPloneUpgradeNeededCommand, self).setUp()
        self.write_zconf_with_test_instance()

    def test_help(self):
        self.upgrade_script('plone_upgrade_needed --help')

    def test_plone_upgrade_already_uptodate(self):
        exitcode, output = self.upgrade_script(
            'plone_upgrade_needed -s plone')
        self.assertEqual(0, exitcode)
        self.assertIn(u'false', output)

    def test_plone_upgrade_needed(self):
        setup = getToolByName(self.portal, 'portal_setup')
        setup.setLastVersionForProfile(_DEFAULT_PROFILE, '4')
        transaction.commit()

        exitcode, output = self.upgrade_script(
            'plone_upgrade_needed -s plone')
        self.assertEqual(0, exitcode)
        self.assertIn(u'true', output)
