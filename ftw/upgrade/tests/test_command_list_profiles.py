from datetime import datetime
from ftw.builder import Builder
from ftw.upgrade.tests.base import CommandAndInstanceTestCase
import json
import re


class TestListProfilesCommand(CommandAndInstanceTestCase):

    def setUp(self):
        super(TestListProfilesCommand, self).setUp()
        self.write_zconf_with_test_instance()

    def test_help(self):
        self.upgrade_script('list --help')
        self.upgrade_script('list profiles --help')

    def test_listing_profiles(self):
        self.package.with_profile(
            Builder('genericsetup profile')
            .with_upgrade(Builder('ftw upgrade step').to(datetime(2011, 1, 1)))
            .with_upgrade(Builder('ftw upgrade step').to(datetime(2012, 2, 2))))

        with self.package_created():
            self.install_profile('the.package:default', version='20110101000000')
            self.clear_recorded_upgrades('the.package:default')

            exitcode, output = self.upgrade_script('list profiles -s plone')
            self.assertEquals(0, exitcode)

            normalized_output = map(unicode.strip,
                                    re.sub(r' +', ' ', output).splitlines())
            self.assertIn('Installed profiles:', normalized_output)
            self.assertIn('the.package:default'
                          ' 2 proposed 1 orphan'
                          ' the.package'
                          ' 20110101000000 / 20120202000000',
                          normalized_output)

    def test_listing_profiles_as_json(self):
        self.package.with_profile(
            Builder('genericsetup profile')
            .with_upgrade(Builder('ftw upgrade step').to(datetime(2011, 1, 1)))
            .with_upgrade(Builder('ftw upgrade step').to(datetime(2012, 2, 2))))

        with self.package_created():
            self.install_profile('the.package:default', version='20110101000000')
            self.clear_recorded_upgrades('the.package:default')

            exitcode, output = self.upgrade_script('list profiles -s plone --json')
            self.assertEquals(0, exitcode)
            self.assert_json_contains_profile(
                {'id': 'the.package:default',
                 'title': 'the.package',
                 'product': 'the.package',
                 'db_version': '20110101000000',
                 'fs_version': '20120202000000',
                 'outdated_fs_version': False,
                 'upgrades': [
                        {'id': '20110101000000@the.package:default',
                         'title': 'Upgrade.',
                         'source': '10000000000000',
                         'dest': '20110101000000',
                         'proposed': True,
                         'done': False,
                         'orphan': True,
                         'outdated_fs_version': False},
                        {'id': '20120202000000@the.package:default',
                         'title': 'Upgrade.',
                         'source': '20110101000000',
                         'dest': '20120202000000',
                         'proposed': True,
                         'done': False,
                         'orphan': False,
                         'outdated_fs_version': False},
                        ]},
                json.loads(output))
