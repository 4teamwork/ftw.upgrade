from unittest2 import TestCase
from ftw.upgrade import utils


class Foo(object):
    pass


class TestUtils(TestCase):

    def test_get_dotted_name(self):
        self.assertEqual(utils.get_dotted_name(Foo),
                         'ftw.upgrade.tests.test_utils.Foo')

    def test_get_modules(self):
        dottedname = 'ftw.upgrade.tests.data.bar'

        expected_modules = set((
            'ftw.upgrade.tests.data.bar',
            'ftw.upgrade.tests.data.bar.one',
            'ftw.upgrade.tests.data.bar.one.baz',
            'ftw.upgrade.tests.data.bar.two',
            'ftw.upgrade.tests.data.bar.two.three',
            'ftw.upgrade.tests.data.bar.two.three.foo',
            ))

        modules = utils.get_modules(dottedname)

        module_names = []

        for module in modules:
            self.assertEqual(type(module).__name__, 'module')
            module_names.append(module.__name__)

        self.assertEqual(len(set(module_names)), len(module_names))

        self.assertEqual(set(module_names), expected_modules)

    def test_filepath_to_dottedname(self):
        self.assertEqual(
            utils.filepath_to_dottedname('/tmp/foo', '/tmp/foo/bar/baz.py'),
            'bar.baz')
            
        self.assertEqual(
            utils.filepath_to_dottedname(
                '/tmp/ftw/upgrade/tests/data/foo/upgrades',
                '/tmp/ftw/upgrade/tests/data/foo/upgrades/testupgrade.py',
                prefix='ftw.upgrade.tests.data.foo.upgrades'),
            'ftw.upgrade.tests.data.foo.upgrades.testupgrade')

        self.assertEqual(
            utils.filepath_to_dottedname('/tmp/foo',
                                         '/tmp/foo/bar/baz/bla.py',
                                         prefix='yeah'),
            'yeah.bar.baz.bla')

        self.assertEqual(
            utils.filepath_to_dottedname('/tmp/foo',
                                         '/tmp/foo/bar/__init__.py'),
            'bar')

        with self.assertRaises(ValueError) as cm:
            utils.filepath_to_dottedname('/tmp/foo/bar', '/tmp/foo')
        self.assertEqual(
            str(cm.exception),
            '`path` (/tmp/foo) does not begin with `basepath` (/tmp/foo/bar)'
            )
