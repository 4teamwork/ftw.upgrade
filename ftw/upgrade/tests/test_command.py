from ftw.upgrade.tests.base import CommandTestCase

import os


class TestCommand(CommandTestCase):

    def test_console_script_created(self):
        path = self.layer['root_path'].joinpath('bin', 'upgrade')
        self.assertTrue(os.path.exists(path), 'Missing executable %s' % path)
        self.assertTrue(os.access(path, os.X_OK), '%s should be executable' % path)

    def test_help_executable(self):
        self.upgrade_script('--help')

    def test_version_executable(self):
        self.upgrade_script('--version')
