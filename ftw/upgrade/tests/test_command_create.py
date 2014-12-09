from ftw.builder import Builder
from ftw.builder import create
from ftw.upgrade.testing import COMMAND_LAYER
from path import Path
from unittest2 import TestCase
import os

class TestCreateCommand(TestCase):
    layer = COMMAND_LAYER

    def test_creating_an_upgrade_step(self):
        paths = create(Builder('package')
                       .within(self.layer.sample_buildout)
                       .with_egginfo())

        self.layer.upgrade_script('create AddControlpanelAction')

        self.assertEqual(
            1, len(os.listdir(paths['upgrades'])),
            'Expected exactly one directory to be generated, got {0}'.format(
                os.listdir(paths['upgrades'])))

        step_name, = os.listdir(paths['upgrades'])
        step_path = os.path.join(paths['upgrades'], step_name)

        self.assertRegexpMatches(step_name, r'^\d{14}_add_controlpanel_action$')
        self.assertEqual(['upgrade.py'], os.listdir(step_path))

        with open(os.path.join(step_path, 'upgrade.py')) as upgrade_file:
            upgrade_code = upgrade_file.read()

        self.maxDiff = True
        self.assertIn('class AddControlpanelAction(UpgradeStep):', upgrade_code)

    def test_creating_an_upgrade_step_with_specifying_upgrades_directory(self):
        paths = create(Builder('package')
                       .within(self.layer.sample_buildout)
                       .with_egginfo())
        subpackage_upgrades_dir = os.path.join(paths['code_directory'], 'subpackage', 'upgrades')
        os.makedirs(subpackage_upgrades_dir)

        self.layer.upgrade_script('create AddControlpanelAction --path {0}'.format(
                subpackage_upgrades_dir))

        self.assertEqual(
            0, len(os.listdir(paths['upgrades'])),
            'Expected default upgrades directory to be empty; {0}'.format(
                os.listdir(paths['upgrades'])))

        self.assertEqual(
            1, len(os.listdir(subpackage_upgrades_dir)),
            'Expected subpackage upgrades directory to have one upgrade; {0}'.format(
                os.listdir(subpackage_upgrades_dir)))

    def test_fails_when_no_egginfo_found(self):
        exitcode, output = self.layer.upgrade_script('create Title', assert_exitcode=False)
        self.assertEqual(1, exitcode, 'command should fail because there is no egg-info')
        self.assertIn('WARNING: no *.egg-info directory could be found.',
                      output)
        self.assertIn('ERROR: Please provide the path to the upgrades directory with --path.',
                      output)

    def test_fails_when_no_upgrades_directory_found(self):
        paths = create(Builder('package').within(self.layer.sample_buildout).with_egginfo())
        Path(paths['upgrades']).rmtree()

        exitcode, output = self.layer.upgrade_script('create Title', assert_exitcode=False)
        self.assertEqual(1, exitcode, 'command should fail because there is no upgrades directory')
        self.assertIn('WARNING: no "upgrades" directory could be found.',
                      output)
        self.assertIn('ERROR: Please provide the path to the upgrades directory with --path.',
                      output)
