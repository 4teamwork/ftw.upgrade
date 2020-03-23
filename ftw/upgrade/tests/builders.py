from ftw.builder import builder_registry
from ftw.builder.utils import serialize_callable
from ftw.upgrade import UpgradeStep
from ftw.upgrade.directory import scaffold
from path import Path

import inflection
import os


class DeferrableUpgrade(UpgradeStep):

    deferrable = True

    def __call__(self):
        pass


class UpgradeStepBuilder(object):

    def __init__(self, session):
        self.session = session
        self.destination_version = None
        self.name = None
        self.package = None
        self.profile_builder = None
        self.named('Upgrade')
        self.code = None
        self.directories = []
        self.files = []
        self.zcml_directory_options = None

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

    def calling(self, callable_, *to_import):
        """Make the upgrade step execute the callable passed as argument.
        The callable will be serialized to a string.

        If the callable is a class, superclasses are automatically imported.
        Other globals are not imported and need to be passed to ``calling``
        as additional positional arguments.
        """

        source = serialize_callable(callable_, *to_import)
        return self.with_code(source)

    def as_deferrable(self):
        return self.calling(DeferrableUpgrade)

    def with_directory(self, relative_path):
        """Create a directory in the profile.
        """
        self.directories.append(relative_path)
        return self

    def with_zcml_directory_options(self, **options):
        """Set additional options in the upgrade-step:directory directive.
        """
        self.zcml_directory_options = options
        return self

    def with_file(self, relative_path, contents, makedirs=False):
        """Create a file within this package.
        """
        if makedirs and Path(relative_path).parent:
            self.with_directory(Path(relative_path).parent)

        self.files.append((relative_path, contents))
        return self

    def create(self):
        if self.destination_version is None:
            raise ValueError('A destination version is required.'
                             ' Use .to(datetime(...)).')
        self._set_package()
        self._declare_zcml_directory()
        name = self._create_upgrade()
        self._register_files_and_dirs_in_package_builder(name)

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
                       directory='.',
                       **(self.zcml_directory_options or {}))
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
            os.path.join(step_name, '__init__.py'),
            '',
            makedirs=True)

        self.package.with_file(
            os.path.join(step_name, 'upgrade.py'),
            self.code)
        return step_name

    def _register_files_and_dirs_in_package_builder(self, step_name):
        for relative_path in self.directories:
            self.package.with_directory(os.path.join(step_name, relative_path))

        for path, contents in self.files:
            self.package.with_file(os.path.join(step_name, path), contents)


builder_registry.register('ftw upgrade step', UpgradeStepBuilder)
