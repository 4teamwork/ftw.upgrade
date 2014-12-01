from ftw.builder import Builder
from ftw.builder import create
from ftw.upgrade.command.utils import find_egginfo
from ftw.upgrade.command.utils import find_package_namespace_path
from ftw.upgrade.testing import COMMAND_LAYER
from ftw.upgrade.tests.helpers import capture_streams
from ftw.upgrade.tests.helpers import chdir
from path import Path
from StringIO import StringIO
from unittest2 import TestCase


class TestFindEgginfo(TestCase):
    layer = COMMAND_LAYER

    def setUp(self):
        self.buildout_path = Path(self.layer.sample_buildout)

    def test_finds_egginfo_in_current_directory(self):
        create(Builder('package')
               .named('test.package')
               .within(self.buildout_path)
               .with_egginfo())

        self.assertEqual(self.buildout_path.joinpath('test.package.egg-info'),
                         find_egginfo(self.buildout_path))

    def test_working_directory_used_when_no_path_passed_to_in(self):
        create(Builder('package')
               .named('test.package')
               .within(self.buildout_path)
               .with_egginfo())

        with chdir(self.buildout_path):
            self.assertEqual(self.buildout_path.joinpath('test.package.egg-info'),
                             find_egginfo())

    def test_prints_warning_when_no_egginfo_found(self):
        stderr = StringIO()
        with capture_streams(stderr=stderr):
            self.assertEqual(None, find_egginfo(self.buildout_path))

        self.assertEquals('WARNING: no *.egg-info directory could be found.\n',
                          stderr.getvalue())

    def test_prints_warning_when_multiple_egginfos_found(self):
        create(Builder('package')
               .named('test.package')
               .within(self.buildout_path)
               .with_egginfo())

        create(Builder('package')
               .named('another.package')
               .within(self.buildout_path)
               .with_egginfo())

        stderr = StringIO()
        with capture_streams(stderr=stderr):
            self.assertEqual(None, find_egginfo(self.buildout_path))

        self.assertEquals('WARNING: more than one *.egg-info directory found.\n',
                          stderr.getvalue())


class TestFindPackageNamespacePath(TestCase):
    layer = COMMAND_LAYER

    def setUp(self):
        self.buildout_path = Path(self.layer.sample_buildout)

    def test_returns_absolute_path_to_toplevel_namespace_directory(self):
        create(Builder('package')
               .named('test.package')
               .within(self.buildout_path)
               .with_egginfo())

        egginfo = find_egginfo(self.buildout_path)
        self.assertEquals(self.buildout_path.joinpath('test'),
                          find_package_namespace_path(egginfo))
