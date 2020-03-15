from Acquisition import aq_chain
from ftw.upgrade.tests.base import CommandAndInstanceTestCase
from ftw.upgrade.utils import get_portal_migration
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.utils import getFSVersionTuple
from unittest import skipIf
from ZPublisher.BaseRequest import RequestContainer
from ZPublisher.HTTPRequest import HTTPRequest

import transaction


class TestPloneUpgradeCommand(CommandAndInstanceTestCase):

    def setUp(self):
        super(TestPloneUpgradeCommand, self).setUp()
        self.write_zconf_with_test_instance()

    def test_help(self):
        self.upgrade_script('plone_upgrade --help')

    def test_plone_upgrade_already_uptodate(self):
        exitcode, output = self.upgrade_script(
            'plone_upgrade -s plone')
        self.assertEqual(0, exitcode)
        transaction.begin()  # sync transaction
        self.assertIn(u'Plone Site was already up to date.', output)

    @skipIf(getFSVersionTuple() > (5, ), 'The test does not work on Plone 5.')
    def test_upgrade_plone(self):
        from Products.CMFPlone.factory import _DEFAULT_PROFILE
        setup = getToolByName(self.portal, 'portal_setup')
        setup.setLastVersionForProfile(_DEFAULT_PROFILE, '4')
        transaction.commit()

        exitcode, output = self.upgrade_script(
            'plone_upgrade -s plone')
        self.assertEqual(0, exitcode)
        transaction.begin()  # sync transaction
        self.assertIn(u'Plone Site has been updated.', output)

    def test_portal_migration_tool_is_wrapped_in_request_container(self):
        portal = self.layer['portal']
        portal_migration = get_portal_migration(portal)

        self.assertIsInstance(portal_migration.REQUEST, HTTPRequest)
        self.assertIsInstance(aq_chain(portal_migration)[-1], RequestContainer)
