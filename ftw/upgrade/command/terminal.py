from __future__ import print_function
from operator import itemgetter
from six.moves import filter
from six.moves import map
from six.moves import zip


class FakeTerminal(str):

    def __getattr__(self, name):
        if name == 'length':
            return len
        return self

    def __getattribute__(self, name):
        if name in ('center', 'ljust', 'lstrip', 'rjust', 'rstrip', 'strip'):
            return lambda text, *a, **kw: getattr(text, name)(*a, **kw)
        return str.__getattribute__(self, name)

    def __call__(self, text):
        return text


try:
    from blessed import Terminal
except ImportError:
    Terminal = FakeTerminal


TERMINAL = Terminal()
FLAGS = {
    'done': TERMINAL.green('done'),
    'orphan': TERMINAL.standout(TERMINAL.red('ORPHAN')),
    'outdated_fs_version': TERMINAL.standout(
        TERMINAL.red('FS-VERSION-OUTDATED')),
    'deferrable': TERMINAL.standout(TERMINAL.blue('DEFERRABLE')),
    'proposed': TERMINAL.blue('proposed')}


def print_table(data, titles=None, colspace=1):
    if titles:
        data.insert(0, list(map(TERMINAL.bright_black, titles)))

    column_lengths = list(map(max, zip(
        *[list(map(TERMINAL.length, row)) for row in data])))
    for row in data:
        for col_num, cell in enumerate(row):
            print(TERMINAL.ljust(cell, column_lengths[col_num] + colspace), end=' ')
        print('')


def upgrade_id_with_flags(upgrade, omit_flags=()):
    flags = set(FLAGS.keys()) - set(omit_flags)
    flagstext = ' '.join(FLAGS.get(flag) for flag in flags
                         if upgrade.get(flag, None))
    return ' '.join((colorize_api_id(upgrade['id']), flagstext)).strip()


def colorize_api_id(api_id):
    dest_version, profileid = api_id.split('@')
    return dest_version + '@' + colorize_profile_id(profileid)


def colorize_profile_id(profile_id):
    return TERMINAL.green(profile_id)


def colorized_profile_versions(profile):
    db_version = profile['db_version']
    fs_version = profile['fs_version']
    if db_version != fs_version:
        db_version = TERMINAL.red(db_version)
    return TERMINAL.bright_black(' / '.join((db_version, fs_version)))


def colorized_profile_flags(profile):
    flags = []
    if profile['outdated_fs_version']:
        flags.append(FLAGS['outdated_fs_version'])

    proposed = len(list(filter(itemgetter('proposed'), profile['upgrades'])))
    if proposed:
        flags.append(TERMINAL.blue('{0} proposed'.format(proposed)))

    orphans = len(list(filter(itemgetter('orphan'), profile['upgrades'])))
    if orphans:
        flags.append(TERMINAL.standout_red('{0} orphan'.format(orphans)))

    return ' '.join(flags)
