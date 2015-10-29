from ftw.upgrade.command.terminal import FakeTerminal
from ftw.upgrade.command.terminal import TERMINAL
from unittest2 import TestCase


class TestFakeTerminal(TestCase):
    """The FakeTerminal is used instead of the blessed terminal when there are import
    problems, such as python not built with _curses support.
    The FakeTerminal should act similar to the Terminal class but not do things such
    as formatting / colorization.
    """

    def test_concatenating_colors(self):
        term = FakeTerminal()
        self.assertEquals(
            'foo',
            term.standout + term.green + term.red_bold + 'foo' + term.normal)

    def test_calling_colors(self):
        term = FakeTerminal()
        self.assertEquals(
            'foo',
            term.red_bold(term.standout('foo')))

    def test_length(self):
        self.assertEquals(3, FakeTerminal().length('foo'))

    def test_ljust(self):
        self.assertEquals(TERMINAL.ljust('foo', 10),
                          FakeTerminal().ljust('foo', 10))
        self.assertEquals(TERMINAL.ljust(u'foo', 10),
                          FakeTerminal().ljust(u'foo', 10))

    def test_rjust(self):
        self.assertEquals(TERMINAL.rjust('foo', 10),
                          FakeTerminal().rjust('foo', 10))

    def test_center(self):
        self.assertEquals(TERMINAL.center('foo', 10),
                          FakeTerminal().center('foo', 10))

    def test_strip(self):
        self.assertEquals(TERMINAL.strip('  foo  '),
                          FakeTerminal().strip('  foo  '))

    def test_rstrip(self):
        self.assertEquals(TERMINAL.rstrip('  foo  '),
                          FakeTerminal().rstrip('  foo  '))

    def test_lstrip(self):
        self.assertEquals(TERMINAL.lstrip('  foo  '),
                          FakeTerminal().lstrip('  foo  '))
