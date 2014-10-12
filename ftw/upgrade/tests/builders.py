from ftw.builder import builder_registry
import os


UPGRADE_CODE = '''
from ftw.upgrade import UpgradeStep

class Upgrade(UpgradeStep):
    """{0}
    """

    def __call__(self):
        self.install_upgrade_profile()
'''

TWO_UPGRADES_CODE = UPGRADE_CODE + '''
class SecondUpgrade(UpgradeStep):
    """{0}
    """

    def __call__(self):
        self.install_upgrade_profile()
'''

class UpgradeStepBuilder(object):

    def __init__(self, session):
        self.session = session
        self.name = None
        self.directory = None
        self.title = None
        self.upgrade_code = UPGRADE_CODE

    def named(self, name):
        self.name = name
        return self

    def titled(self, title):
        self.title = title
        return self

    def within(self, directory):
        self.directory = directory
        return self

    def with_upgrade_code(self, code_string):
        self.upgrade_code = code_string
        return self

    def create(self, **kwargs):
        self.validate()
        path = os.path.join(self.directory, self.name)
        os.mkdir(path)
        with open(os.path.join(path, 'upgrade.py'), 'w+') as upgrade_file:
            upgrade_file.write(self.upgrade_code.format(self.title or self.name))
        return path

    def validate(self):
        assert self.name is not None, \
            'Upgrade step requires a name; use named()'
        assert self.directory is not None, \
            'Upgrade step requires a directory; use within()'
        assert os.path.isdir(self.directory), \
            'Path is not a directory: {0}'.format(self.directory)


builder_registry.register('upgrade step', UpgradeStepBuilder)
