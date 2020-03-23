from datetime import datetime
from ftw.testing import freeze
from ftw.upgrade.directory.scaffold import UpgradeStepCreator
from unittest import TestCase

import os.path
import re
import shutil
import tempfile


class TestUpgradeStepCreator(TestCase):

    def setUp(self):
        self.upgrades_directory = tempfile.mkdtemp('ftw.upgrade.tests')

    def tearDown(self):
        shutil.rmtree(self.upgrades_directory)

    def test_generates_directory_and_upgrade_code(self):
        with freeze(datetime(2014, 11, 14, 22, 44, 55)):
            UpgradeStepCreator(self.upgrades_directory).create('AddControlpanelAction')

        upgrade_directory = os.path.join(self.upgrades_directory,
                                         '20141114224455_add_controlpanel_action')
        upgrade_code_file = os.path.join(upgrade_directory, 'upgrade.py')

        self.assertTrue(os.path.isdir(upgrade_directory))
        self.assertTrue(os.path.isfile(upgrade_code_file))
        with open(upgrade_code_file) as python_file:
            code = python_file.read()

        self.maxDiff = None
        self.assertMultiLineEqual(
            '\n'.join((
                    'from ftw.upgrade import UpgradeStep',
                    '',
                    '',
                    'class AddControlpanelAction(UpgradeStep):',
                    '    """Add controlpanel action.',
                    '    """',
                    '',
                    '    def __call__(self):',
                    '        self.install_upgrade_profile()',
                    '')),
            code)

    def test_generate_upgrade_step_by_camelcase_name(self):
        with freeze(datetime(2014, 11, 14, 22, 44, 55)):
            UpgradeStepCreator(self.upgrades_directory).create('AddControlpanelAction')

        self.assert_upgrade({'name': '20141114224455_add_controlpanel_action',
                             'classname': 'AddControlpanelAction',
                             'docstring': 'Add controlpanel action.'})

    def test_generate_upgrade_step_by_underscore_name(self):
        with freeze(datetime(2014, 11, 14, 22, 44, 55)):
            UpgradeStepCreator(self.upgrades_directory).create('add_controlpanel_action')

        self.assert_upgrade({'name': '20141114224455_add_controlpanel_action',
                             'classname': 'AddControlpanelAction',
                             'docstring': 'Add controlpanel action.'})

    def test_generate_upgrade_step_by_humanized_name(self):
        with freeze(datetime(2014, 11, 14, 22, 44, 55)):
            UpgradeStepCreator(self.upgrades_directory).create('Add controlpanel action')

        self.assert_upgrade({'name': '20141114224455_add_controlpanel_action',
                             'classname': 'AddControlpanelAction',
                             'docstring': 'Add controlpanel action.'})

    def test_sentence_as_input_is_used_as_docstring_without_modification(self):
        with freeze(datetime(2014, 3, 4, 5, 6, 7)):
            UpgradeStepCreator(self.upgrades_directory).create(
                'Update ftw.subsite to newest Version.')

        self.assert_upgrade(
            {'name': '20140304050607_update_ftw_subsite_to_newest_version',
             'classname': 'UpdateFtwSubsiteToNewestVersion',
             'docstring': 'Update ftw.subsite to newest Version.'})

    def assert_upgrade(self, expected):
        upgrade_directory = os.path.join(self.upgrades_directory, expected['name'])
        upgrade_code_file = os.path.join(upgrade_directory, 'upgrade.py')

        self.assertTrue(os.path.isdir(upgrade_directory),
                        os.listdir(os.path.dirname(upgrade_directory)))
        self.assertTrue(os.path.isfile(upgrade_code_file))

        with open(upgrade_code_file) as python_file:
            code = python_file.read()

        got = {'name': expected['name'],
               'classname': re.search('class ([^\(]*)\(UpgradeStep\):', code).group(1),
               'docstring': re.compile('"""(.*?)"""', re.DOTALL).search(code).group(1).strip()}
        self.assertDictEqual(expected, got)
