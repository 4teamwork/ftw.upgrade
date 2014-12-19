from ftw.builder import builder_registry
from ftw.upgrade.directory import scaffold
import inflection
import os


class UpgradeStepBuilder(object):

    def __init__(self, session):
        self.session = session
        self.destination_version = None
        self.name = None
        self.package = None
        self.profile_builder = None
        self.named('Upgrade')
        self.code = None

    def to(self, destination):
        if hasattr(destination, 'strftime'):
            self.destination_version = destination.strftime(scaffold.DATETIME_FORMAT)
        else:
            self.destination_version = destination
        return self

    def named(self, name):
        self.name = name
        return self

    def for_profile(self, profile_builder):
        self.profile_builder = profile_builder
        if self.profile_builder.fs_version is None:
            self.profile_builder.with_fs_version(False)
        return self

    def with_code(self, code_as_string):
        self.code = code_as_string
        return self

    def create(self):
        if self.destination_version is None:
            raise ValueError('A destination version is required.'
                             ' Use .to(datetime(...)).')
        self._set_package()
        self._declare_zcml_directory()
        return self._create_upgrade()

    def _set_package(self):
        self.package = self.profile_builder.package.get_subpackage('upgrades')
        if self.profile_builder.name != 'default':
            self.package = self.package.get_subpackage(self.profile_builder.name)

    def _declare_zcml_directory(self):
        zcml = self.package.get_configure_zcml()

        if getattr(zcml, '_upgrade_step_declarations', None) is None:
            zcml._upgrade_step_declarations = {}

        if zcml._upgrade_step_declarations.get(self.profile_builder.name):
            return

        zcml.include('ftw.upgrade', file='meta.zcml')
        zcml.with_node('upgrade-step:directory',
                       profile=self.profile_builder.profile_name,
                       directory='.')
        zcml._upgrade_step_declarations[self.profile_builder.name] = True

    def _create_upgrade(self):
        name = self.name.replace(' ', '_').replace('\.$', '')
        step_name = '{0}_{1}'.format(self.destination_version,
                                     inflection.underscore(name))
        if self.code is None:
            self.code = scaffold.PYTHON_TEMPLATE.format(
                classname=inflection.camelize(name),
                docstring=inflection.humanize(
                    inflection.underscore(name)))

        self.package.with_file(
            os.path.join(step_name, 'upgrade.py'),
            self.code,
            makedirs=True)
        return step_name


builder_registry.register('ftw upgrade step', UpgradeStepBuilder)
