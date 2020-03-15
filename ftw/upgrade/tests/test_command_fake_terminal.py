from ftw.upgrade.command.terminal import FakeTerminal
from ftw.upgrade.command.terminal import TERMINAL
from unittest import TestCase


class TestFakeTerminal(TestCase):
    """The FakeTerminal is used instead of the blessed terminal when there are import
    problems, such as python not built with _curses support.
    The FakeTerminal should act similar to the Terminal class but not do things such
    as formatting / colorization.
    """

    def test_concatenating_colors(self):
        term = FakeTerminal()
        self.assertEqual(
            'foo',
            term.standout + term.green + term.red_bold + 'foo' + term.normal)

    def test_calling_colors(self):
        term = FakeTerminal()
        self.assertEqual(
            'foo',
            term.red_bold(term.standout('foo')))

    def test_length(self):
        self.assertEqual(3, FakeTerminal().length('foo'))

    def test_ljust(self):
        self.assertEqual(TERMINAL.ljust('foo', 10),
                         FakeTerminal().ljust('foo', 10))
        self.assertEqual(TERMINAL.ljust(u'foo', 10),
                         FakeTerminal().ljust(u'foo', 10))

    def test_rjust(self):
        self.assertEqual(TERMINAL.rjust('foo', 10),
                         FakeTerminal().rjust('foo', 10))

    def test_center(self):
        self.assertEqual(TERMINAL.center('foo', 10),
                         FakeTerminal().center('foo', 10))

    def test_strip(self):
        self.assertEqual(TERMINAL.strip('  foo  '),
                         FakeTerminal().strip('  foo  '))

    def test_rstrip(self):
        self.assertEqual(TERMINAL.rstrip('  foo  '),
                         FakeTerminal().rstrip('  foo  '))

    def test_lstrip(self):
        self.assertEqual(TERMINAL.lstrip('  foo  '),
                         FakeTerminal().lstrip('  foo  '))
