from datetime import datetime
from path import Path

import inflection
import os
import re


PYTHON_TEMPLATE = '''from ftw.upgrade import UpgradeStep


class {classname}(UpgradeStep):
    """{docstring}.
    """

    def __call__(self):
        self.install_upgrade_profile()
'''

DATETIME_FORMAT = '%Y%m%d%H%M%S'


class UpgradeStepCreator(object):

    def __init__(self, upgrades_directory):
        self.upgrades_directory = upgrades_directory

    def create(self, name):
        docstring = name.rstrip('.')
        name = re.sub('\W', '_', name.rstrip('.'))

        if re.match('^\w*$', docstring):
            # docstring seems to not be a sentence but a camelcase classname
            # or a underscored upgrade directory name.
            # Lets make it human readable for use as docstring.
            docstring = inflection.humanize(
                inflection.underscore(name))

        step_name = '{0}_{1}'.format(
            datetime.now().strftime(DATETIME_FORMAT),
            inflection.underscore(name))
        step_directory = os.path.join(self.upgrades_directory, step_name)
        os.mkdir(step_directory)

        Path(step_directory).joinpath('__init__.py').touch()

        code_path = os.path.join(step_directory, 'upgrade.py')
        with open(code_path, 'w+') as code_file:
            code_file.write(
                PYTHON_TEMPLATE.format(
                    classname=inflection.camelize(name),
                    docstring=docstring))

        return step_directory
