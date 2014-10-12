from ftw.builder import Builder
from ftw.builder import create
from ftw.builder.testing import BUILDER_LAYER
from ftw.upgrade.directory.scanner import Scanner
from ftw.upgrade.exceptions import UpgradeStepDefinitionError
from ftw.upgrade.tests.builders import TWO_UPGRADES_CODE
from unittest2 import TestCase
import os.path
import shutil
import tempfile


class TestDirectoryScanner(TestCase):

    layer = BUILDER_LAYER

    def setUp(self):
        self.upgrades_directory = tempfile.mkdtemp('ftw.upgrade.tests')
        open(os.path.join(self.upgrades_directory, '__init__.py'), 'w+').close()

    def tearDown(self):
        shutil.rmtree(self.upgrades_directory)

    def test_returns_chained_upgrade_infos(self):
        add_path = create(Builder('upgrade step')
                          .named('20110101080000_add_action')
                          .titled('Add an action')
                          .within(self.upgrades_directory))

        update_path = create(Builder('upgrade step')
                             .named('20110202080000_update_action')
                             .titled('Update the action')
                             .within(self.upgrades_directory))

        remove_path = create(Builder('upgrade step')
                             .named('20110303080000_remove_action')
                             .titled('Remove the action')
                             .within(self.upgrades_directory))

        upgrade_infos = Scanner('ftw.upgrade.tests', self.upgrades_directory).scan()
        # "callable" should contain the upgrade step class object.
        # It is not easy to compare this, therfore we cast it to bool.
        map(lambda info: info.update(callable=bool(info['callable'])), upgrade_infos)

        self.maxDiff = None
        self.assertEqual(
            [{'source-version': None,
              'target-version': '20110101080000',
              'title': 'Add an action',
              'path': add_path,
              'callable': True},

             {'source-version': '20110101080000',
              'target-version': '20110202080000',
              'title': 'Update the action',
              'path': update_path,
              'callable': True},

             {'source-version': '20110202080000',
              'target-version': '20110303080000',
              'title': 'Remove the action',
              'path': remove_path,
              'callable': True}],

            upgrade_infos)

    def test_exception_raised_when_no_upgrade_code(self):
        create(Builder('upgrade step')
               .named('20110101080000_add_action')
               .with_upgrade_code('')
               .within(self.upgrades_directory))

        with self.assertRaises(UpgradeStepDefinitionError) as cm:
            Scanner('ftw.upgrade.tests', self.upgrades_directory).scan()

        self.assertEqual(
            'The upgrade step 20110101080000_add_action has no upgrade class'
            ' in the upgrade.py module.',
            str(cm.exception))

    def test_exception_raised_when_multiple_upgrade_steps_detected(self):
        create(Builder('upgrade step')
               .named('20110101080000_add_action')
               .with_upgrade_code(TWO_UPGRADES_CODE)
               .within(self.upgrades_directory))

        with self.assertRaises(UpgradeStepDefinitionError) as cm:
            Scanner('ftw.upgrade.tests', self.upgrades_directory).scan()

        self.assertEqual(
            'The upgrade step 20110101080000_add_action has more than one upgrade'
            ' class in the upgrade.py module.',
            str(cm.exception))

    def test_does_not_fail_when_no_upgrades_present(self):
        upgrade_infos = Scanner('ftw.upgrade.tests', self.upgrades_directory).scan()
        self.assertEqual([], upgrade_infos)
