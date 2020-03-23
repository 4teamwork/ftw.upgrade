from ftw.builder import Builder
from ftw.builder import create
from ftw.builder.testing import BUILDER_LAYER
from ftw.testing.layer import TempDirectoryLayer
from ftw.upgrade.command.utils import find_egginfo
from ftw.upgrade.command.utils import find_package_namespace_path
from ftw.upgrade.tests.helpers import capture_streams
from ftw.upgrade.tests.helpers import chdir
from path import Path
from six import StringIO
from unittest import TestCase


LAYER = TempDirectoryLayer(bases=(BUILDER_LAYER, ),
                           name='ftw.upgrade.test_command_utils')


class TestFindEgginfo(TestCase):
    layer = LAYER

    def setUp(self):
        self.path = Path(self.layer['temp_directory']).realpath()
        self.package_builder = (Builder('python package')
                                .named('the.package')
                                .at_path(self.path))

    def test_finds_egginfo_in_current_directory(self):
        create(self.package_builder)
        self.assertEqual(self.path.joinpath('the.package.egg-info'),
                         find_egginfo(self.path))

    def test_working_directory_used_when_no_path_passed_to_in(self):
        create(self.package_builder)
        with chdir(self.path):
            self.assertEqual(self.path.joinpath('the.package.egg-info'),
                             find_egginfo())

    def test_prints_warning_when_no_egginfo_found(self):
        stderr = StringIO()
        with capture_streams(stderr=stderr):
            self.assertEqual(None, find_egginfo(self.path))

        self.assertEqual('WARNING: no *.egg-info directory could be found.\n',
                         stderr.getvalue())

    def test_prints_warning_when_multiple_egginfos_found(self):
        create(self.package_builder)
        create(Builder('python package').named('another.package').at_path(self.path))

        stderr = StringIO()
        with capture_streams(stderr=stderr):
            self.assertEqual(None, find_egginfo(self.path))

        self.assertEqual('WARNING: more than one *.egg-info directory found.\n',
                         stderr.getvalue())


class TestFindPackageNamespacePath(TestCase):
    layer = LAYER

    def setUp(self):
        self.path = Path(self.layer['temp_directory']).realpath()

    def test_returns_absolute_path_to_toplevel_namespace_directory(self):
        create(Builder('python package').named('the.package').at_path(self.path))
        egginfo = find_egginfo(self.path)
        self.assertEqual(self.path.joinpath('the'),
                         find_package_namespace_path(egginfo))
