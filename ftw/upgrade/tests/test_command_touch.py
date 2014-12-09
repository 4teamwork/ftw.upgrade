from datetime import datetime
from ftw.builder import Builder
from ftw.builder import create
from ftw.upgrade.testing import COMMAND_LAYER
from ftw.upgrade.tests.builders import UPGRADE_CODE
from unittest2 import TestCase
import os


class TestTouchCommand(TestCase):
    layer = COMMAND_LAYER

    def test_touching_an_upgrade_step_renews_the_timestamp(self):
        paths = create(Builder('package').within(self.layer.sample_buildout))
        upgrade_path = create(Builder('upgrade step')
                              .named('20110101080000_add_action')
                              .within(paths['upgrades']))

        self.assertTrue(os.path.exists(upgrade_path),
                        'Expected path to exist: {0}'.format(upgrade_path))
        self.layer.upgrade_script('touch {0}'.format(upgrade_path))
        self.assertFalse(os.path.exists(upgrade_path),
                         'Expected path to no longer exist: {0}'.format(upgrade_path))

        step_name, = os.listdir(paths['upgrades'])
        self.assertRegexpMatches(step_name,
                                 r'^{0}\d{{10}}_add_action'.format(datetime.now().year))

    def test_moving_after_another(self):
        paths = create(Builder('package').within(self.layer.sample_buildout))

        add_path = create(Builder('upgrade step')
                          .named('20111105000000_add_action')
                          .within(paths['upgrades']))

        create(Builder('upgrade step')
               .named('20111125000000_remove_action')
               .within(paths['upgrades']))

        update_path = create(Builder('upgrade step')
                             .named('20221212111111_update_action')
                             .within(paths['upgrades']))

        self.layer.upgrade_script('touch {0} --after {1}'.format(update_path, add_path))

        self.assertEqual(['20111105000000_add_action',
                          '20111115000000_update_action',
                          '20111125000000_remove_action'],
                         sorted(os.listdir(paths['upgrades'])))

    def test_moving_explicitly_to_the_end(self):
        paths = create(Builder('package').within(self.layer.sample_buildout))
        remove_path = create(Builder('upgrade step')
                             .named('20221212111111_remove_action')
                             .within(paths['upgrades']))

        add_path = create(Builder('upgrade step')
                          .named('20111105000055_add_action')
                          .within(paths['upgrades']))

        self.layer.upgrade_script('touch {0} --after {1}'.format(remove_path, add_path))

        self.assertEqual(['20111105000055_add_action',
                          '20111106000055_remove_action'],
                         sorted(os.listdir(paths['upgrades'])))

    def test_moving_before_another(self):
        paths = create(Builder('package').within(self.layer.sample_buildout))
        create(Builder('upgrade step')
               .named('20111105000000_add_action')
               .within(paths['upgrades']))

        remove_path = create(Builder('upgrade step')
                             .named('20111125000000_remove_action')
                             .within(paths['upgrades']))

        update_path = create(Builder('upgrade step')
                             .named('20221212111111_update_action')
                             .within(paths['upgrades']))

        self.layer.upgrade_script('touch {0} --before {1}'.format(update_path, remove_path))

        self.assertEqual(['20111105000000_add_action',
                          '20111115000000_update_action',
                          '20111125000000_remove_action'],
                         sorted(os.listdir(paths['upgrades'])))

    def test_moving_explicitly_to_the_beginning(self):
        paths = create(Builder('package').within(self.layer.sample_buildout))
        remove_path = create(Builder('upgrade step')
                             .named('20111106000055_remove_action')
                             .within(paths['upgrades']))

        add_path = create(Builder('upgrade step')
                          .named('20221212111111_add_action')
                          .within(paths['upgrades']))

        self.layer.upgrade_script('touch {0} --before {1}'.format(add_path, remove_path))

        self.assertEqual(['20111105000055_add_action',
                          '20111106000055_remove_action'],
                         sorted(os.listdir(paths['upgrades'])))

    def test_moving_before_and_after_at_same_time_is_not_allowed(self):
        paths = create(Builder('package').within(self.layer.sample_buildout))
        add_path = create(Builder('upgrade step')
                          .named('20111105000000_add_action')
                          .within(paths['upgrades']))

        remove_path = create(Builder('upgrade step')
                             .named('20111125000000_remove_action')
                             .within(paths['upgrades']))

        update_path = create(Builder('upgrade step')
                             .named('20221212111111_update_action')
                             .within(paths['upgrades']))

        args = 'touch {0} --before {1} --after {2}'.format(add_path, remove_path, update_path)
        exitcode, output = self.layer.upgrade_script(args, assert_exitcode=False)
        self.assertEqual(2, exitcode, 'command should fail because --after and --before can'
                         ' not be used at the same time.')
        self.assertIn('error: argument --after/-a: not allowed with argument --before/-b',
                      output)

    def test_moving_upgrade_step_should_not_import_upgrade_step(self):
        """The bin/upgrade path does usually only include ftw.upgrade (and dependencies)
        but not the path of the package in development or its dependencies.
        Therefore the bin/upgrade command should not import any code.
        """
        paths = create(Builder('package').within(self.layer.sample_buildout))
        first_path = create(Builder('upgrade step')
                            .named('20111111020202_migrate_content_type')
                            .within(paths['upgrades'])
                            .with_upgrade_code('from any.package.content import thing\n' +
                                               UPGRADE_CODE))

        second_path = create(Builder('upgrade step')
                             .named('20121212030303_add_action')
                             .within(paths['upgrades']))

        self.layer.upgrade_script('touch {0} --before {1}'.format(second_path, first_path))

        self.assertEqual(['20111110020202_add_action',
                          '20111111020202_migrate_content_type'],
                         sorted(os.listdir(paths['upgrades'])))
