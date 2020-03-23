from ftw.upgrade.tests.base import CommandAndInstanceTestCase

import json


class TestSitesCommand(CommandAndInstanceTestCase):

    def setUp(self):
        super(TestSitesCommand, self).setUp()
        self.write_zconf_with_test_instance()

    def test_sites_help(self):
        self.upgrade_script('sites --help')

    def test_listing_sites_as_table(self):
        exitcode, output = self.upgrade_script('sites')
        self.assertEqual(0, exitcode)
        self.assertEqual('/plone               Plone site\n', output)

    def test_listing_sites_as_json(self):
        exitcode, output = self.upgrade_script('sites --json')
        self.assertEqual(0, exitcode)
        self.assert_json_equal([{'id': 'plone',
                                 'path': '/plone',
                                 'title': 'Plone site'}],
                               json.loads(output))

    def test_error_when_no_site_reachable(self):
        self.layer['root_path'].joinpath('parts/instance').rmtree()
        exitcode, output = self.upgrade_script('sites', assert_exitcode=False)
        self.assertEqual(1, exitcode)
        self.assertMultiLineEqual(
            'ERROR: No running Plone instance detected.\n',
            output)
