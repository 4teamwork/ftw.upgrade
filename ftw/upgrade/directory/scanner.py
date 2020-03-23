from ftw.upgrade import UpgradeStep
from ftw.upgrade.exceptions import UpgradeStepDefinitionError
from ftw.upgrade.utils import subject_from_docstring
from functools import reduce
from glob import glob
from Products.GenericSetup.upgrade import normalize_version
from six.moves import filter
from six.moves import map

import imp
import inspect
import os.path
import re
import six


UPGRADESTEP_DATETIME_REGEX = re.compile(r'^.*/?(\d{14})[^/]*/upgrade.py$')


class Scanner(object):

    def __init__(self, dottedname, directory):
        self.dottedname = dottedname
        self.directory = directory

    def scan(self):
        self._load_upgrades_directory()
        infos = list(map(self._build_upgrade_step_info,
                         self._find_upgrade_directories()))
        infos.sort(key=lambda info: normalize_version(info['target-version']))
        if len(infos) > 0:
            reduce(self._chain_upgrade_steps, infos)
        return infos

    def _find_upgrade_directories(self):
        return list(filter(UPGRADESTEP_DATETIME_REGEX.match,
                           glob('{0}/*/upgrade.py'.format(self.directory))))

    def _build_upgrade_step_info(self, path):
        title, callable = self._load_upgrade_step_code(path)
        return {'source-version': None,
                'target-version':
                    UPGRADESTEP_DATETIME_REGEX.match(path).group(1),
                'path': os.path.dirname(path),
                'title': title,
                'callable': callable}

    def _chain_upgrade_steps(self, first, second):
        second['source-version'] = first['target-version']
        return second

    def _load_upgrade_step_code(self, upgrade_path):
        path = os.path.dirname(upgrade_path)

        try:
            fp, pathname, description = imp.find_module('.', [path])
        except ImportError:
            pass
        else:
            name = '.'.join((self.dottedname, os.path.basename(path)))
            imp.load_module(name, fp, pathname, description)

        fp, pathname, description = imp.find_module('upgrade', [path])
        name = '.'.join((self.dottedname,
                         os.path.basename(path),
                         'upgrade'))

        module = imp.load_module(name, fp, pathname, description)
        upgrade_steps = tuple(self._find_upgrade_step_classes_in_module(
                module))

        if len(upgrade_steps) == 0:
            raise UpgradeStepDefinitionError(
                'The upgrade step {0} has no upgrade class in the'
                ' upgrade.py module.'.format(os.path.basename(path)))

        if len(upgrade_steps) > 1:
            raise UpgradeStepDefinitionError(
                'The upgrade step {0} has more than one upgrade class in the'
                ' upgrade.py module.'.format(os.path.basename(path)))

        return upgrade_steps[0]

    def _find_upgrade_step_classes_in_module(self, module):
        for name, value in inspect.getmembers(module, inspect.isclass):
            if not issubclass(value, UpgradeStep):
                continue

            if inspect.getmodule(value) is not module:
                continue

            title = subject_from_docstring(inspect.getdoc(value) or name)
            title = six.ensure_text(title)
            yield (title, value)

    def _load_upgrades_directory(self):
        """This method tries to load the upgrade step directory, if there is
        an __init__.py. This helps to avoid RuntimeWarnings.
        However, it is not relevant for anything to work,
        it just makes Python happy.
        """
        try:
            fp, pathname, description = imp.find_module('.', [self.directory])
        except ImportError:
            pass
        else:
            imp.load_module(self.dottedname, fp, str(pathname), description)
