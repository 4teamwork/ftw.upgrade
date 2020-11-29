from contextlib import contextmanager
from datetime import datetime
from ftw.builder import Builder
from ftw.builder import create
from ftw.upgrade.directory.scanner import Scanner
from ftw.upgrade.exceptions import UpgradeStepDefinitionError
from ftw.upgrade.tests.base import UpgradeTestCase
from six.moves import map

import six
import unittest


class TestDirectoryScanner(UpgradeTestCase):

    def setUp(self):
        super(TestDirectoryScanner, self).setUp()
        self.profile = Builder('genericsetup profile')
        self.package.with_profile(self.profile)

    def test_returns_chained_upgrade_infos(self):
        self.profile.with_upgrade(Builder('ftw upgrade step')
                                  .to(datetime(2011, 1, 1, 8))
                                  .named('add an action'))
        self.profile.with_upgrade(Builder('ftw upgrade step')
                                  .to(datetime(2011, 2, 2, 8))
                                  .named('update the action'))
        self.profile.with_upgrade(Builder('ftw upgrade step')
                                  .to(datetime(2011, 3, 3, 8))
                                  .named('remove the action'))

        with self.scanned() as upgrade_infos:
            list(map(lambda info: (info.__delitem__('path'),
                                   info.__delitem__('callable')),
                     upgrade_infos))

            self.maxDiff = None
            self.assertEqual(
                [{'source-version': None,
                  'target-version': '20110101080000',
                  'title': 'Add an action.'},

                 {'source-version': '20110101080000',
                  'target-version': '20110202080000',
                  'title': 'Update the action.'},

                 {'source-version': '20110202080000',
                  'target-version': '20110303080000',
                  'title': 'Remove the action.'}],

                upgrade_infos)

    @unittest.skipUnless(
        six.PY2, "Loading upgrades uses a deprecated library in Python2.7"
    )
    def test_exception_raised_when_upgrade_has_no_code_py27(self):
        self.profile.with_upgrade(Builder('ftw upgrade step')
                                  .to(datetime(2011, 1, 1, 8))
                                  .named('add action')
                                  .with_code(''))

        with create(self.package) as package:
            with self.assertRaises(UpgradeStepDefinitionError) as cm:
                self.scan(package)

        self.assertEqual(
            'The upgrade step 20110101080000_add_action has no upgrade class'
            ' in the upgrade.py module.',
            str(cm.exception))

    @unittest.skipUnless(
        six.PY2, "Loading upgrades uses a deprecated library in Python2.7"
    )
    def test_exception_raised_when_multiple_upgrade_steps_detected_py27(self):
        code = '\n'.join((
                'from ftw.upgrade import UpgradeStep',
                'class Foo(UpgradeStep): pass',
                'class Bar(UpgradeStep): pass'))

        self.profile.with_upgrade(Builder('ftw upgrade step')
                                  .to(datetime(2011, 1, 1, 8))
                                  .named('add action')
                                  .with_code(code))

        with create(self.package) as package:
            with self.assertRaises(UpgradeStepDefinitionError) as cm:
                self.scan(package)

        self.assertEqual(
            'The upgrade step 20110101080000_add_action has more than one upgrade'
            ' class in the upgrade.py module.',
            str(cm.exception))

    @unittest.skipIf(
        six.PY2, "Loading upgrades uses a deprecated library in Python2.7"
    )
    def test_exception_raised_when_upgrade_has_no_code(self):
        self.profile.with_upgrade(Builder('ftw upgrade step')
                                  .to(datetime(2011, 1, 1, 8))
                                  .named('add action')
                                  .with_code(''))

        with create(self.package) as package:
            with self.assertRaises(UpgradeStepDefinitionError) as cm:
                self.scan(package)
        self.assertRegex(
            str(cm.exception),
            "The upgrade step file (.*)upgrade.py has no upgrade class."  # noqa: E501
        )

    @unittest.skipIf(
        six.PY2, "Loading upgrades uses a deprecated library in Python2.7"
    )
    def test_exception_raised_when_multiple_upgrade_steps_detected(self):
        code = '\n'.join((
                'from ftw.upgrade import UpgradeStep',
                'class Foo(UpgradeStep): pass',
                'class Bar(UpgradeStep): pass'))

        self.profile.with_upgrade(Builder('ftw upgrade step')
                                  .to(datetime(2011, 1, 1, 8))
                                  .named('add action')
                                  .with_code(code))

        with create(self.package) as package:
            with self.assertRaises(UpgradeStepDefinitionError) as cm:
                self.scan(package)
        self.assertRegex(
            str(cm.exception),
            "The upgrade step file (.*)upgrade.py has more than one upgrade class."  # noqa: E501
        )

    def test_does_not_fail_when_no_upgrades_present(self):
        self.package.with_zcml_include('ftw.upgrade', file='meta.zcml')
        self.package.with_zcml_node('upgrade-step:directory',
                                    profile='the.package:default',
                                    directory='.')

        with self.scanned() as upgrade_infos:
            self.assertEqual( [], upgrade_infos)

    @contextmanager
    def scanned(self):
        with create(self.package) as package:
            yield self.scan(package)

    def scan(self, package):
        upgrades = package.package_path.joinpath('upgrades')
        return Scanner('the.package.upgrades', upgrades).scan()
