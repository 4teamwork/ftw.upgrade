from datetime import datetime
from ftw.builder import Builder
from ftw.upgrade.tests.base import CommandAndInstanceTestCase
from six.moves import map

import json
import re
import six


class TestListCommand(CommandAndInstanceTestCase):

    def setUp(self):
        super(TestListCommand, self).setUp()
        self.write_zconf_with_test_instance()

    def test_help(self):
        self.upgrade_script('list --help')

    def test_listing_profiles(self):
        self.package.with_profile(
            Builder('genericsetup profile')
            .with_upgrade(Builder('ftw upgrade step').to(datetime(2011, 1, 1)))
            .with_upgrade(Builder('ftw upgrade step').to(datetime(2012, 2, 2))))

        with self.package_created():
            self.install_profile('the.package:default', version='20110101000000')
            self.clear_recorded_upgrades('the.package:default')

            exitcode, output = self.upgrade_script('list --profiles -s plone')
            self.assertEqual(0, exitcode)

            normalized_output = list(map(six.text_type.strip,
                                         re.sub(r' +', ' ', output).splitlines()))
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

            exitcode, output = self.upgrade_script('list --profiles -s plone --json')
            self.assertEqual(0, exitcode)
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
                         'deferrable': False,
                         'done': False,
                         'orphan': True,
                         'outdated_fs_version': False},
                        {'id': '20120202000000@the.package:default',
                         'title': 'Upgrade.',
                         'source': '20110101000000',
                         'dest': '20120202000000',
                         'proposed': True,
                         'deferrable': False,
                         'done': False,
                         'orphan': False,
                         'outdated_fs_version': False},
                        ]},
                json.loads(output))

    def test_listing_proposed_upgrades(self):
        self.package.with_profile(
            Builder('genericsetup profile')
            .with_upgrade(Builder('ftw upgrade step').to(datetime(2011, 1, 1)))
            .with_upgrade(Builder('ftw upgrade step').to(datetime(2012, 2, 2))))

        with self.package_created():
            self.install_profile('the.package:default', version='20110101000000')
            self.clear_recorded_upgrades('the.package:default')

            exitcode, output = self.upgrade_script('list --upgrades -s plone')
            self.assertEqual(0, exitcode)
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

            exitcode, output = self.upgrade_script('list --upgrades -s plone --json')
            self.assertEqual(0, exitcode)
            self.assert_json_equal(
                [{
                        "dest": "20110101000000",
                        "done": False,
                        "id": "20110101000000@the.package:default",
                        "orphan": True,
                        "outdated_fs_version": False,
                        "proposed": True,
                        "deferrable": False,
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
                        "deferrable": False,
                        "source": "20110101000000",
                        "title": "Upgrade."
                        }],
                json.loads(output))

    def test_deferrable_upgrades_are_annotated_in_list(self):
        self.package.with_profile(
            Builder('genericsetup profile')
            .with_upgrade(Builder('ftw upgrade step')
                          .to(datetime(2011, 1, 1))
                          .as_deferrable()))

        with self.package_created():
            self.install_profile('the.package:default', version='1')
            self.clear_recorded_upgrades('the.package:default')

            exitcode, output = self.upgrade_script('list --upgrades -s plone')
            self.assertEqual(0, exitcode)

            self.assertMultiLineEqual(
                u'Proposed upgrades:\n'
                'ID:                                            Title:             \n'
                '20110101000000@the.package:default DEFERRABLE  DeferrableUpgrade  \n',
                output)

    def test_orphaned_is_omitted_in_listing_for_deferrable_upgrades(self):
        self.package.with_profile(
            Builder('genericsetup profile')
            .with_upgrade(Builder('ftw upgrade step').to(datetime(2011, 1, 1)).as_deferrable())
            .with_upgrade(Builder('ftw upgrade step').to(datetime(2012, 2, 2))))

        with self.package_created():
            self.install_profile('the.package:default', version='20110101000000')
            self.clear_recorded_upgrades('the.package:default')

            exitcode, output = self.upgrade_script('list --upgrades -s plone')
            self.assertEqual(0, exitcode)
            self.assertMultiLineEqual(
                'Proposed upgrades:\n'
                'ID:                                            Title:             \n'
                '20110101000000@the.package:default DEFERRABLE  DeferrableUpgrade  \n'
                '20120202000000@the.package:default             Upgrade.           \n',
                output)

    def test_listing_deferrable_upgrades_as_json(self):
        self.package.with_profile(
            Builder('genericsetup profile')
            .with_upgrade(Builder('ftw upgrade step')
                          .to(datetime(2011, 1, 1))
                          .as_deferrable()))

        with self.package_created():
            self.install_profile('the.package:default', version='1')
            self.clear_recorded_upgrades('the.package:default')

            exitcode, output = self.upgrade_script('list --upgrades -s plone --json')
            self.assertEqual(0, exitcode)
            self.assert_json_equal(
                [{
                        "dest": "20110101000000",
                        "done": False,
                        "id": "20110101000000@the.package:default",
                        "orphan": False,
                        "outdated_fs_version": False,
                        "proposed": True,
                        "deferrable": True,
                        "source": "10000000000000",
                        "title": "DeferrableUpgrade"
                        }],
                json.loads(output))

    def test_pick_site_argument(self):
        self.package.with_profile(
            Builder('genericsetup profile')
            .with_upgrade(Builder('ftw upgrade step').to(datetime(2011, 1, 1))))

        with self.package_created():
            self.install_profile('the.package:default', version='20110101000000')
            self.clear_recorded_upgrades('the.package:default')

            exitcode, output = self.upgrade_script('list --upgrades --json --pick-site')
            self.assertEqual(1, len(json.loads(output)))

    def test_last_site_argument(self):
        self.package.with_profile(
            Builder('genericsetup profile')
            .with_upgrade(Builder('ftw upgrade step').to(datetime(2011, 1, 1))))

        with self.package_created():
            self.install_profile('the.package:default', version='20110101000000')
            self.clear_recorded_upgrades('the.package:default')

            exitcode, output = self.upgrade_script('list --upgrades --json --pick-site')
            self.assertEqual(1, len(json.loads(output)))

    def test_all_sites_argument_json(self):
        self.package.with_profile(
            Builder('genericsetup profile')
            .with_upgrade(
                Builder('ftw upgrade step').to(datetime(2011, 1, 1))))

        with self.package_created():
            self.install_profile(
                'the.package:default', version='20110101000000')
            self.clear_recorded_upgrades('the.package:default')

            exitcode, output = self.upgrade_script(
                'list --upgrades --json --all-sites')
            self.assertEqual(exitcode, 0)
            decoded = json.loads(output)
            self.assertEqual(len(decoded), 1)
            # The Plone site id is used as key.
            self.assertEqual(list(decoded.keys()), ['/plone'])
            self.assertTrue(isinstance(decoded['/plone'], list))

    def test_all_sites_argument_no_json(self):
        self.package.with_profile(
            Builder('genericsetup profile')
            .with_upgrade(
                Builder('ftw upgrade step').to(datetime(2011, 1, 1))))

        with self.package_created():
            self.install_profile(
                'the.package:default', version='20110101000000')
            self.clear_recorded_upgrades('the.package:default')

            exitcode, output = self.upgrade_script(
                'list --upgrades --all-sites')
            self.assertEqual(exitcode, 0)
            self.assertIn('Proposed upgrades', output)
            self.assertIn('20110101000000@the.package:default', output)
            self.assertIn('INFO: Acting on site /plone', output)
