from ftw.upgrade.tests.base import CommandTestCase


class TestHelpCommand(CommandTestCase):

    def test_help(self):
        exitcode, output = self.upgrade_script('help')
        self.assertTrue(output)

    def test_subcommand_help(self):
        exitcode, output = self.upgrade_script('help create')
        self.assertTrue(output)
