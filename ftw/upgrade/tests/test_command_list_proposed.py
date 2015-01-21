from datetime import datetime
from ftw.builder import Builder
from ftw.upgrade.tests.base import CommandAndInstanceTestCase
import json


class TestListProposedCommand(CommandAndInstanceTestCase):

    def setUp(self):
        super(TestListProposedCommand, self).setUp()
        self.write_zconf_with_test_instance()

    def test_help(self):
        self.upgrade_script('list --help')
        self.upgrade_script('list proposed --help')

    def test_listing_proposed_upgrades(self):
        self.package.with_profile(
            Builder('genericsetup profile')
            .with_upgrade(Builder('ftw upgrade step').to(datetime(2011, 1, 1)))
            .with_upgrade(Builder('ftw upgrade step').to(datetime(2012, 2, 2))))

        with self.package_created():
            self.install_profile('the.package:default', version='20110101000000')
            self.clear_recorded_upgrades('the.package:default')

            exitcode, output = self.upgrade_script('list proposed -s plone')
            self.assertEquals(0, exitcode)
            self.assertMultiLineEqual(
                'Proposed upgrades:\n'
                'ID:                                        Title:    \n'
                '20110101000000@the.package:default ORPHAN  Upgrade.  \n'
                '20120202000000@the.package:default         Upgrade.  \n',
                output)

    def test_listing_proposed_upgrades_as_json(self):
        self.package.with_profile(
            Builder('genericsetup profile')
            .with_upgrade(Builder('ftw upgrade step').to(datetime(2011, 1, 1)))
            .with_upgrade(Builder('ftw upgrade step').to(datetime(2012, 2, 2))))

        with self.package_created():
            self.install_profile('the.package:default', version='20110101000000')
            self.clear_recorded_upgrades('the.package:default')

            exitcode, output = self.upgrade_script('list proposed -s plone --json')
            self.assertEquals(0, exitcode)
            self.assert_json_equal(
                [{
                        "dest": "20110101000000",
                        "done": False,
                        "id": "20110101000000@the.package:default",
                        "orphan": True,
                        "outdated_fs_version": False,
                        "proposed": True,
                        "source": "10000000000000",
                        "title": "Upgrade."
                        },
                 {
                        "dest": "20120202000000",
                        "done": False,
                        "id": "20120202000000@the.package:default",
                        "orphan": False,
                        "outdated_fs_version": False,
                        "proposed": True,
                        "source": "20110101000000",
                        "title": "Upgrade."
                        }],
                json.loads(output))
