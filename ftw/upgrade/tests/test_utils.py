from unittest2 import TestCase
from ftw.upgrade import utils


class Foo(object):
    pass


class TestUtils(TestCase):

    def test_get_dotted_name(self):
        self.assertEqual(utils.get_dotted_name(Foo),
                         'ftw.upgrade.tests.test_utils.Foo')
