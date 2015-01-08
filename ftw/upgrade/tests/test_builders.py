from datetime import datetime
from ftw.builder import Builder
from ftw.upgrade import UpgradeStep
from ftw.upgrade.tests.base import UpgradeTestCase
from Products.CMFCore.utils import getToolByName


class TestUpgradeStepBuilder(UpgradeTestCase):

    def setUp(self):
        super(TestUpgradeStepBuilder, self).setUp()
        self.profile = Builder('genericsetup profile')
        self.package.with_profile(self.profile)

    def test_upgrade_step_directory_and_file_is_created(self):
        self.profile.with_upgrade(Builder('ftw upgrade step')
                                  .to(datetime(2011, 1, 1))
                                  .named('migrate file content type'))

        with self.package_created() as package:
            upgrade_path = package.package_path.joinpath(
                'upgrades', '20110101000000_migrate_file_content_type')
            self.assertTrue(upgrade_path.isdir(),
                            'Upgrade directory was not created {0}'.format(upgrade_path))
            self.assertMultiLineEqual(
                '\n'.join(('from ftw.upgrade import UpgradeStep',
                           '',
                           '',
                           'class MigrateFileContentType(UpgradeStep):',
                           '    """Migrate file content type.',
                           '    """',
                           '',
                           '    def __call__(self):',
                           '        self.install_upgrade_profile()',
                           '')),
                upgrade_path.joinpath('upgrade.py').text())

    def test_executing_upgrade_step_with_custom_code(self):
        class AddExcludeFromNavIndex(UpgradeStep):
            def __call__(self):
                self.catalog_add_index('excludeFromNav', 'KeywordIndex')

        self.profile.with_upgrade(Builder('ftw upgrade step')
                                  .to(datetime(2011, 1, 1))
                                  .calling(AddExcludeFromNavIndex))

        catalog = getToolByName(self.portal, 'portal_catalog')
        with self.package_created():
            self.install_profile('the.package:default', '0')
            self.assertNotIn('excludeFromNav', catalog.indexes(),
                             'Index excludeFromNav already exists.')
            self.install_profile_upgrades('the.package:default')
            self.assertIn('excludeFromNav', catalog.indexes(),
                          'Index excludeFromNav was not created.')

    def test_add_files_and_directories_to_profile(self):
        self.profile.with_upgrade(
            Builder('ftw upgrade step')
            .to(datetime(2011, 1, 1))
            .with_file('foo.txt', 'FOO')
            .with_directory('bar')
            .with_file('baz/baz.txt', 'BAZ', makedirs=True))

        with self.package_created() as package:
            upgrade_path = package.package_path.joinpath('upgrades',
                                                         '20110101000000_upgrade')
            self.assertTrue(upgrade_path.isdir(),
                            'Upgrade directory was not created {0}'.format(upgrade_path))

            self.assertEqual('FOO', upgrade_path.joinpath('foo.txt').text())
            self.assertTrue(upgrade_path.joinpath('bar').isdir(),
                            'directory "bar" was not created.')
            self.assertEqual('BAZ', upgrade_path.joinpath('baz', 'baz.txt').text())

    def test_importing_upgrade_step_with_import_profile_files(self):
        self.profile.with_upgrade(
            Builder('ftw upgrade step')
            .to(datetime(2011, 1, 1))
            .with_file('properties.xml', self.asset('foo-property.xml')))

        with self.package_created():
            self.install_profile('the.package:default', '0')
            self.assertFalse(self.portal.getProperty('foo'),
                             'Expected property "foo" to not yet exist.')
            self.install_profile_upgrades('the.package:default')
            self.assertEqual('bar',
                             self.portal.getProperty('foo'),
                             'Property "foo" was not created.')
