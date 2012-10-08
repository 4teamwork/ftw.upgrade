from ftw.upgrade.utils import SizedGenerator
from ftw.upgrade.utils import topological_sort
from unittest2 import TestCase


class TestTopologicalSort(TestCase):

    def test_simple(self):
        items = ['b', 'a', 'c']
        dependencies = (
            ('a', 'b'),
            ('b', 'c'))

        self.assertEqual(topological_sort(items, dependencies),
                         ['a', 'b', 'c'])

    def test_advanced(self):
        items = ['a', 'c', 'b', 'd']
        dependencies = (
            ('a', 'b'),
            ('a', 'c'),
            ('b', 'd'),
            ('b', 'c'))

        self.assertEqual(topological_sort(items, dependencies),
                         ['a', 'b', 'c', 'd'])

    def test_duplicated(self):
        items = ['a', 'b', 'a']
        dependencies = (
            ('b', 'a'),
            )

        self.assertEqual(topological_sort(items, dependencies),
                         ['b', 'a'])

    def test_cyclic(self):
        items = ['a', 'b']
        dependencies = (
            ('a', 'b'),
            ('b', 'a'))

        self.assertEqual(topological_sort(items, dependencies),
                         None)


class TestSizedGenerator(TestCase):

    def test_length(self):
        generator = SizedGenerator((i for i in range(3)), 3)
        self.assertEqual(len(generator), 3)

    def test_iterating(self):
        generator = SizedGenerator((i for i in range(3)), 3)
        self.assertEqual(list(generator), [0, 1, 2])
