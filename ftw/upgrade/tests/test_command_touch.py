from datetime import datetime
from ftw.builder import Builder
from ftw.builder import create
from ftw.upgrade.tests.base import CommandTestCase

import six


class TestTouchCommand(CommandTestCase):

    def setUp(self):
        self.package_builder = (Builder('python package')
                                .named('the.package')
                                .at_path(self.layer.sample_buildout))
        self.package = None

    def test_touching_an_upgrade_step_renews_the_timestamp(self):
        self.package = create(
            self.package_builder
            .with_profile(Builder('genericsetup profile')
                          .with_upgrade(Builder('ftw upgrade step')
                                        .to(datetime(2011, 1, 1))
                                        .named('AddAction'))))

        path = self.package.package_path.joinpath('upgrades', '20110101000000_add_action')
        self.assertTrue(
            path.exists(),
            'Expected path to exist: {0}'.format(path))
        self.upgrade_script('touch {0}'.format(path))
        self.assertFalse(path.exists(),
                         'Expected path to no longer exist: {0}'.format(path))

        new_step_path, = path.dirname().dirs()
        six.assertRegex(
            self, new_step_path.name,
            r'^{0}\d{{10}}_add_action'.format(datetime.now().year))

    def test_moving_after_another(self):
        self.package = create(
            self.package_builder
            .with_profile(Builder('genericsetup profile')
                          .with_upgrade(Builder('ftw upgrade step')
                                        .to(datetime(2011, 11, 5))
                                        .named('add_action'))
                          .with_upgrade(Builder('ftw upgrade step')
                                        .to(datetime(2011, 11, 25))
                                        .named('remove_action'))
                          .with_upgrade(Builder('ftw upgrade step')
                                        .to(datetime(2022, 12, 12))
                                        .named('update_action'))))

        self.upgrade_script('touch {update_action} --after {add_action}'.format(
                **self.upgrades()))
        self.assert_upgrades('20111105000000_add_action',
                             '20111115000000_update_action',
                             '20111125000000_remove_action')

    def test_moving_explicitly_to_the_end(self):
        self.package = create(
            self.package_builder
            .with_profile(Builder('genericsetup profile')
                          .with_upgrade(Builder('ftw upgrade step')
                                        .to(datetime(2022, 12, 12, 0, 0, 0))
                                        .named('remove_action'))
                          .with_upgrade(Builder('ftw upgrade step')
                                        .to(datetime(2011, 11, 5, 0, 0, 55))
                                        .named('add_action'))))

        self.upgrade_script('touch {remove_action} --after {add_action}'.format(
                **self.upgrades()))

        self.assert_upgrades('20111105000055_add_action',
                             '20111106000055_remove_action')

    def test_moving_before_another(self):
        self.package = create(
            self.package_builder
            .with_profile(Builder('genericsetup profile')
                          .with_upgrade(Builder('ftw upgrade step')
                                        .to(datetime(2011, 11, 5))
                                        .named('add_action'))
                          .with_upgrade(Builder('ftw upgrade step')
                                        .to(datetime(2011, 11, 25))
                                        .named('remove_action'))
                          .with_upgrade(Builder('ftw upgrade step')
                                        .to(datetime(2022, 12, 12))
                                        .named('update_action'))))

        self.upgrade_script('touch {update_action} --before {remove_action}'.format(
                **self.upgrades()))

        self.assert_upgrades('20111105000000_add_action',
                             '20111115000000_update_action',
                             '20111125000000_remove_action')

    def test_moving_explicitly_to_the_beginning(self):
        self.package = create(
            self.package_builder
            .with_profile(Builder('genericsetup profile')
                          .with_upgrade(Builder('ftw upgrade step')
                                        .to(datetime(2011, 11, 6, 0, 0, 55))
                                        .named('remove_action'))
                          .with_upgrade(Builder('ftw upgrade step')
                                        .to(datetime(2022, 12, 12, 12, 12, 12))
                                        .named('add_action'))))

        self.upgrade_script('touch {add_action} --before {remove_action}'.format(
                **self.upgrades()))

        self.assert_upgrades('20111105000055_add_action',
                             '20111106000055_remove_action')

    def test_moving_before_and_after_at_same_time_is_not_allowed(self):
        self.package = create(
            self.package_builder
            .with_profile(Builder('genericsetup profile')
                          .with_upgrade(Builder('ftw upgrade step')
                                        .to(datetime(2011, 1, 1))
                                        .named('add_action'))
                          .with_upgrade(Builder('ftw upgrade step')
                                        .to(datetime(2011, 1, 2))
                                        .named('remove_action'))
                          .with_upgrade(Builder('ftw upgrade step')
                                        .to(datetime(2022, 1, 3))
                                        .named('update action'))))

        cmd = 'touch {add_action} --before {remove_action} --after {update_action}'.format(
            **self.upgrades())
        exitcode, output = self.upgrade_script(cmd, assert_exitcode=False)
        self.assertEqual(2, exitcode, 'command should fail because --after and --before can'
                         ' not be used at the same time.')
        self.assertIn('error: argument --after/-a: not allowed with argument --before/-b',
                      output)

    def test_moving_upgrade_step_should_not_import_upgrade_step(self):
        """The bin/upgrade path does usually only include ftw.upgrade (and dependencies)
        but not the path of the package in development or its dependencies.
        Therefore the bin/upgrade command should not import any code.
        """

        code = 'raise AssertionError("Upgrade code should not be imported..")'
        self.package = create(
            self.package_builder
            .with_profile(Builder('genericsetup profile')
                          .with_upgrade(Builder('ftw upgrade step')
                                        .to(datetime(2022, 12, 12, 0, 0, 0))
                                        .named('remove_action')
                                        .with_code(code))
                          .with_upgrade(Builder('ftw upgrade step')
                                        .to(datetime(2011, 11, 5, 0, 0, 55))
                                        .named('add_action')
                                        .with_code(code))))

        self.upgrade_script('touch {remove_action} --after {add_action}'.format(
                **self.upgrades()))

        self.assert_upgrades('20111105000055_add_action',
                             '20111106000055_remove_action')

    def upgrades(self):
        upgrades_dir = self.package.package_path.joinpath('upgrades')
        self.assertTrue(upgrades_dir.isdir(),
                        '"upgrades" directory is missing at {0}'.format(upgrades_dir))
        return dict([(path.name.split('_', 1)[1], path) for path in upgrades_dir.dirs()])

    def assert_upgrades(self, *expected):
        upgrades_dir = self.package.package_path.joinpath('upgrades')
        self.assertTrue(upgrades_dir.isdir(),
                        '"upgrades" directory is missing at {0}'.format(upgrades_dir))
        expected = set(expected)
        got = set([str(path.name) for path in upgrades_dir.dirs()])
        self.assertEqual(expected, got, 'Unexpected upgrades.')
