from blessed import Terminal


TERMINAL = Terminal()
FLAGS = {
    'done': TERMINAL.green('done'),
    'orphan': TERMINAL.standout(TERMINAL.red('ORPHAN')),
    'outdated_fs_version': TERMINAL.standout(
        TERMINAL.red('FS-VERSION-OUTDATED')),
    'proposed': TERMINAL.blue('proposed')}


def print_table(data, titles=None, colspace=1):
    if titles:
        data.insert(0, map(TERMINAL.bright_black, titles))

    column_lengths = map(max, zip(*map(
                lambda row: map(TERMINAL.length, row), data)))
    for row in data:
        for col_num, cell in enumerate(row):
            print TERMINAL.ljust(cell, column_lengths[col_num] + colspace),
        print ''


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
