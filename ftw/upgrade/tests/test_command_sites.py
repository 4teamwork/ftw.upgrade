from ftw.upgrade.tests.base import CommandAndInstanceTestCase
from plone.app.testing import SITE_OWNER_NAME
from plone.app.testing import TEST_USER_PASSWORD
import json
import os


class TestSitesCommand(CommandAndInstanceTestCase):

    def setUp(self):
        super(TestSitesCommand, self).setUp()
        self.write_zconf_with_test_instance()

    def test_sites_help(self):
        self.upgrade_script('sites --help')

    def test_listing_sites_as_table(self):
        exitcode, output = self.upgrade_script('sites')
        self.assertEquals(0, exitcode)
        self.assertEquals('/plone               Plone site\n', output)

    def test_listing_sites_as_json(self):
        exitcode, output = self.upgrade_script('sites --json')
        self.assertEquals(0, exitcode)
        self.assert_json_equal([{'id': 'plone',
                                 'path': '/plone',
                                 'title': 'Plone site'}],
                               json.loads(output))

    def test_error_when_no_site_reachable(self):
        self.layer['root_path'].joinpath('parts/instance').rmtree()
        exitcode, output = self.upgrade_script('sites', assert_exitcode=False)
        self.assertEquals(1, exitcode)
        self.assertMultiLineEqual(
            'ERROR: No running Plone instance detected.\n',
            output)

    def test_authentication_by_param(self):
        del os.environ['UPGRADE_AUTHENTICATION']
        exitcode, output = self.upgrade_script('sites --auth {0}:{1}'.format(
                SITE_OWNER_NAME, TEST_USER_PASSWORD))
        self.assertEquals(0, exitcode)
        self.assertEquals('/plone               Plone site\n', output)

    def test_authentication_is_required(self):
        del os.environ['UPGRADE_AUTHENTICATION']
        exitcode, output = self.upgrade_script('sites', assert_exitcode=False)
        self.assertEquals(1, exitcode)
        self.assertEquals('ERROR: No authentication information provided.',
                          output.splitlines()[0])

    def test_valid_authentication_format_is_required(self):
        exitcode, output = self.upgrade_script('sites --auth=john', assert_exitcode=False)
        self.assertEquals(1, exitcode)
        self.assertEquals('ERROR: Invalid authentication information "john".',
                          output.splitlines()[0])
