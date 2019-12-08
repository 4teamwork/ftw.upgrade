from ftw.upgrade.tests.base import CommandAndInstanceTestCase
from Products.CMFPlone.utils import getFSVersionTuple
from unittest import skipIf

import transaction


class TestCombineBundlesCommand(CommandAndInstanceTestCase):
    def setUp(self):
        super(TestCombineBundlesCommand, self).setUp()
        self.write_zconf_with_test_instance()

    def test_help(self):
        self.upgrade_script('combine_bundles --help')

    @skipIf(getFSVersionTuple() < (5,), 'The test only works on Plone 5+.')
    def test_combine_bundles(self):
        with self.assert_bundles_combined():
            exitcode, output = self.upgrade_script('combine_bundles -s plone')
            self.assertEqual('OK\n', output)
            transaction.begin()
