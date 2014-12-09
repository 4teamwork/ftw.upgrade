from ftw.upgrade.testing import COMMAND_LAYER
from unittest2 import TestCase
import os

class TestCommand(TestCase):
    layer = COMMAND_LAYER

    def test_console_script_created(self):
        path = self.layer.upgrade_script_path
        self.assertTrue(os.path.exists(path), 'Missing executable %s' % path)
        self.assertTrue(os.access(path, os.X_OK), '%s should be executable' % path)

    def test_help_executable(self):
        self.layer.upgrade_script('--help')

    def test_version_executable(self):
        self.layer.upgrade_script('--version')
