# Source: http://bugs.python.org/issue12806

from ftw.upgrade.command.terminal import TERMINAL

import argparse
import re
import textwrap


def translate(text):
    if text in ('positional arguments',
                'optional arguments'):
        return TERMINAL.bold(_(text).upper())
    else:
        return _(text)


_ = argparse._
argparse._ = translate


class FlexiFormatter(argparse.RawTextHelpFormatter):
    """FlexiFormatter which respects new line formatting and wraps the rest

    Example:
        >>> parser = argparse.ArgumentParser(formatter_class=FlexiFormatter)
        >>> parser.add_argument('--example', help='''\
        ...     This argument's help text will have this first long line\
        ...     wrapped to fit the target window size so that your text\
        ...     remains flexible.
        ...
        ...         1. This option list
        ...         2. is still persisted
        ...         3. and the option strings get wrapped like this with an\
        ...            indent for readability.
        ...
        ...     You must use backslashes at the end of lines to indicate that\
        ...     you want the text to wrap instead of preserving the newline.
        ...
        ...     As with docstrings, the leading space to the text block is\
        ...     ignored.
        ... ''')
        >>> parser.parse_args(['-h'])
        usage: argparse_formatter.py [-h] [--example EXAMPLE]

        optional arguments:
          -h, --help         show this help message and exit
          --example EXAMPLE  This argument's help text will have this first
                             long line wrapped to fit the target window size
                             so that your text remains flexible.

                                 1. This option list
                                 2. is still persisted
                                 3. and the option strings get wrapped like
                                    this with an indent for readability.

                             You must use backslashes at the end of lines to
                             indicate that you want the text to wrap instead
                             of preserving the newline.

                             As with docstrings, the leading space to the
                             text block is ignored.

    Only the name of this class is considered a public API. All the methods
    provided by the class are considered an implementation detail.
    """

    def _fill_text(self, text, width, indent):
        text = (re.compile('\[quote\].*?\[\/quote\]', re.DOTALL)
                .sub(lambda match: (
                    match.group(0)
                    .replace('\n', '[QUOTE:NEWLINE]')),
                     text))

        text = '\n'.join([indent + line for line
                          in self._split_lines(text, width)])

        text = (re.compile('\[quote\](.*?)\[\/quote\]', re.DOTALL)
                .sub(lambda match: TERMINAL.green(
                    match.group(1)
                    .replace('\n', ' ')
                    .replace('[QUOTE:NEWLINE]',
                             TERMINAL.normal + '\n    ' + TERMINAL.green)
                    .rstrip(' ').strip('\n')),
                     text))
        return text

    def _split_lines(self, text, width):
        lines = list()
        main_indent = TERMINAL.length(re.match(r'( *)', text).group(1))
        # Wrap each line individually to allow for partial formatting
        for line in text.splitlines():

            # Get this line's indent and figure out what indent to use
            # if the line wraps. Account for lists of small variety.
            indent = TERMINAL.length(re.match(r'( *)', line).group(1))
            list_match = re.match(r'( *)(([*-+>]+|\w+\)|\w+\.) +)', line)
            if(list_match):
                sub_indent = indent + TERMINAL.length(list_match.group(2))
            else:
                sub_indent = indent

            # Textwrap will do all the hard work for us
            line = self._whitespace_matcher.sub(' ', line).strip()
            new_lines = textwrap.wrap(
                text=line,
                width=width,
                initial_indent=' ' * (indent - main_indent),
                subsequent_indent=' ' * (sub_indent - main_indent),
            )

            # Blank lines get eaten by textwrap, put it back with [' ']
            lines.extend(new_lines or [' '])

        return lines
