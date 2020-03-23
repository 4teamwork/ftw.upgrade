from ftw.upgrade.tests.base import CommandAndInstanceTestCase

import transaction


class TestRecookCommand(CommandAndInstanceTestCase):

    def setUp(self):
        super(TestRecookCommand, self).setUp()
        self.write_zconf_with_test_instance()

    def test_help(self):
        self.upgrade_script('recook --help')

    def test_recook_resources(self):
        with self.assert_resources_recooked():
            exitcode, output = self.upgrade_script('recook -s plone')
            self.assertEqual('OK\n', output)
            transaction.begin()
