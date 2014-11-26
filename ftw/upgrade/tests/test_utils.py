from ftw.testing import MockTestCase
from ftw.upgrade.exceptions import CyclicDependencies
from ftw.upgrade.utils import find_cyclic_dependencies
from ftw.upgrade.utils import format_duration
from ftw.upgrade.utils import get_sorted_profile_ids
from ftw.upgrade.utils import SizedGenerator
from ftw.upgrade.utils import subject_from_docstring
from ftw.upgrade.utils import topological_sort
from unittest2 import TestCase


class TestTopologicalSort(TestCase):

    def test_simple(self):
        items = ['b', 'a', 'c']
        dependencies = (
            ('a', 'b'),
            ('b', 'c'))

        self.assertEqual(['a', 'b', 'c'],
                         topological_sort(items, dependencies))

    def test_advanced(self):
        items = ['a', 'c', 'b', 'd']
        dependencies = (
            ('a', 'b'),
            ('a', 'c'),
            ('b', 'd'),
            ('b', 'c'))

        self.assertEqual(['a', 'b', 'c', 'd'],
                         topological_sort(items, dependencies))

    def test_duplicated(self):
        items = ['a', 'b', 'a']
        dependencies = (
            ('b', 'a'),
            )

        self.assertEqual(['b', 'a'],
                         topological_sort(items, dependencies))

    def test_cyclic(self):
        items = ['a', 'b']
        dependencies = (
            ('a', 'b'),
            ('b', 'a'))

        self.assertEqual(None,
                         topological_sort(items, dependencies))

    def test_root_nodes_are_reversed_ordered(self):
        items = ['policy', 'xy', 'foo']

        self.assertEqual(
            ['xy', 'policy', 'foo'],
            topological_sort(items, (('policy', 'foo'),)))

        self.assertEqual(
            ['xy', 'policy', 'foo'],
            topological_sort(reversed(items), (('policy', 'foo'),)),
            'items input order should not change result order')


class TestFindCyclicDependencies(TestCase):

    def test_direct_cyclic_dependencies(self):
        dependencies = (
            ('bar', 'foo'),
            ('baz', 'foo'),
            ('baz', 'bar'),
            ('foo', 'bar'),
            ('default', 'file-replacement'),
            ('default', 'image-replacement'),
            )

        self.assertEquals(
            [set(('foo',
                  'bar'))],
            map(set, find_cyclic_dependencies(dependencies)))

    def test_indirect_cyclic_dependencies(self):
        dependencies = (
            ('foo', 'bar'),
            ('bar', 'baz'),
            ('baz', 'foo'),
            )

        self.assertEquals(
            [set(('foo',
                  'bar',
                  'baz'))],
            map(set, find_cyclic_dependencies(dependencies)))


class TestSizedGenerator(TestCase):

    def test_length(self):
        generator = SizedGenerator((i for i in range(3)), 3)
        self.assertEqual(3, len(generator))

    def test_iterating(self):
        generator = SizedGenerator((i for i in range(3)), 3)
        self.assertEqual([0, 1, 2], list(generator))


class TestSortedProfileIds(MockTestCase):

    def test_dependencies_resolved(self):
        portal_setup = self.mocker.mock()
        self.expect(portal_setup.listProfileInfo()).result([
                {'id': 'baz',
                 'dependencies': [
                        'profile-foo',
                        'profile-bar']},

                {'id': 'foo'},

                {'id': 'bar',
                 'dependencies': ['profile-foo']}]).count(1, 2)

        self.replay()

        self.assertEqual(
            ['foo', 'bar', 'baz'],
            get_sorted_profile_ids(portal_setup))

    def test_root_profiles_are_ordered_by_profile_name(self):
        """In the this example the profiles "baz" and "xy"
        have no dependencies to another and thus might be
        ordered in any order from the graph point of view.
        However, we want a cosistent ordern and therefore
        order those root nodes by name.
        """
        portal_setup = self.mocker.mock()
        self.expect(portal_setup.listProfileInfo()).result([
                {'id': 'baz',
                 'dependencies': [
                        'profile-foo']},
                {'id': 'foo'},
                {'id': 'xy'}]).count(1, 2)

        self.replay()

        self.assertEqual(
            ['foo', 'baz', 'xy'],
            get_sorted_profile_ids(portal_setup))

    def test_cyclic_dependencies(self):
        portal_setup = self.mocker.mock()
        self.expect(portal_setup.listProfileInfo()).result([
                {'id': 'foo',
                 'dependencies': ['profile-bar']},

                {'id': 'bar',
                 'dependencies': ['profile-foo']},

                {'id': 'baz',
                 'dependencies': []}]).count(1, 2)

        self.replay()

        with self.assertRaises(CyclicDependencies) as cm:
            get_sorted_profile_ids(portal_setup)

        self.assertEqual([('foo', 'bar')],
                         cm.exception.cyclic_dependencies)

        self.assertEqual([('foo', 'bar'), ('bar', 'foo')],
                         cm.exception.dependencies)


class TestFormatDuration(TestCase):

    def test_zero_seconds_is_supported(self):
        self.assertEqual('0 seconds', format_duration(0))

    def test_single_second_is_singular(self):
        self.assertEqual('1 second', format_duration(1))

    def test_multiple_seconds_is_plural(self):
        self.assertEqual('2 seconds', format_duration(2))

    def test_single_minute_is_singular(self):
        self.assertEqual(['1 minute',
                          '1 minute, 1 second',
                          '1 minute, 2 seconds'],

                         [format_duration(60),
                          format_duration(60 + 1),
                          format_duration(60 + 2)])

    def test_multiple_minutes_is_plural(self):
        self.assertEqual(['2 minutes, 1 second',
                          '2 minutes, 2 seconds'],

                         [format_duration((2 * 60) + 1),
                          format_duration((2 * 60) + 2)])

    def test_single_hour_is_singular(self):
        self.assertEqual(['1 hour',
                          '1 hour, 1 minute',
                          '1 hour, 2 minutes, 1 second',
                          '1 hour, 2 minutes, 2 seconds'],

                         [format_duration((60 * 60)),
                          format_duration((60 * 60) + 60),
                          format_duration((60 * 60) + (2 * 60) + 1),
                          format_duration((60 * 60) + (2 * 60) + 2)])

    def test_multiple_hours_is_plural(self):
        self.assertEqual(['2 hours',
                          '2 hours, 1 minute',
                          '2 hours, 2 minutes, 1 second',
                          '2 hours, 2 minutes, 2 seconds'],

                         [format_duration((2 * 60 * 60)),
                          format_duration((2 * 60 * 60) + 60),
                          format_duration((2 * 60 * 60) + (2 * 60) + 1),
                          format_duration((2 * 60 * 60) + (2 * 60) + 2)])

    def test_floating_point_seconds_are_ceiled(self):
        self.assertEqual(['1 second',
                          '1 second',
                          '2 seconds',
                          '2 seconds'],

                         [format_duration(0.1),
                          format_duration(0.9),
                          format_duration(1.1),
                          format_duration(1.9)])


class TestSubjectFromDocstring(TestCase):

    def test_one_line_only(self):
        self.assertEquals(
            'This is the subject.',
            subject_from_docstring('This is the subject.'))

    def test_whitespace_is_stripped(self):
        self.assertEquals(
            'This is the subject.',
            subject_from_docstring('\nThis is the subject.\n'))

    def test_only_subject_is_returned(self):
        self.assertEquals(
            'This is the subject.',
            subject_from_docstring('This is the subject.\n\nThis is the body.'))

    def test_multiline_subject_is_joined(self):
        self.assertEquals(
            'This is a subject, with multiple lines.',
            subject_from_docstring('This is a subject,\n'
                                   'with multiple lines.\n'
                                   '\n'
                                   'And the body.'))
