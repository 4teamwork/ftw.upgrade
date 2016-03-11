from datetime import datetime
from ftw.builder import Builder
from ftw.builder import create
from ftw.upgrade.tests.base import UpgradeTestCase
from Products.CMFPlone.interfaces import IMigratingPloneSiteRoot
from Products.GenericSetup.interfaces import EXTENSION
from zope.configuration.config import ConfigurationExecutionError


class TestDirectoryMetaDirective(UpgradeTestCase):

    def setUp(self):
        super(TestDirectoryMetaDirective, self).setUp()
        self.profile = Builder('genericsetup profile')
        self.package.with_profile(self.profile)

    def test_upgrade_steps_are_registered(self):
        self.profile.with_upgrade(Builder('ftw upgrade step')
                                  .to(datetime(2011, 1, 1, 8))
                                  .named('add_action'))
        self.profile.with_upgrade(Builder('ftw upgrade step')
                                  .to(datetime(2011, 2, 2, 8))
                                  .named('remove_action'))

        with self.package_created():
            self.assert_upgrades([
                    {'source': ('10000000000000',),
                     'dest': ('20110101080000',),
                     'title': u'Add action.'},

                    {'source': ('20110101080000',),
                     'dest': ('20110202080000',),
                     'title': u'Remove action.'}])

    def test_first_source_version_is_last_regulare_upgrade_step(self):
        self.profile.with_upgrade(Builder('plone upgrade step')
                                  .upgrading('1000', to='1001')
                                  .titled('Register foo utility.'))
        self.profile.with_upgrade(Builder('ftw upgrade step')
                                  .to(datetime(2011, 1, 1, 8))
                                  .named('add_action'))

        with self.package_created():
            self.assert_upgrades([
                    {'source': ('1000',),
                     'dest': ('1001',),
                     'title': u'Register foo utility.'},

                    {'source': ('1001',),
                     'dest': ('20110101080000',),
                     'title': u'Add action.'}])

    def test_registers_migration_generic_setup_profile_foreach_step(self):
        self.profile.with_upgrade(Builder('ftw upgrade step')
                                  .to(datetime(2011, 1, 1, 8))
                                  .named('add_an_action'))

        with self.package_created() as package:
            upgrade_path = package.package_path.joinpath(
                'upgrades', '20110101080000_add_an_action')
            self.assert_profile(
                {'id': 'the.package.upgrades:default-upgrade-20110101080000',
                 'title': 'Upgrade the.package:default ' + \
                     'to 20110101080000: Add an action.',
                 'description': '',
                 'path': upgrade_path,
                 'product': 'the.package.upgrades',
                 'type': EXTENSION,
                 'for': IMigratingPloneSiteRoot})

    def test_package_modules_is_not_corrupted(self):
        # Regression: when the upgrade-step:directory directive is used from
        # the package-directory with a relative path (directory="upgrades"),
        # it corrupted the sys.modules entry of the package.

        package_builder = (
            Builder('python package')
            .named('other.package')
            .at_path(self.layer['temp_directory'])
            .with_file('__init__.py', 'PACKAGE = "package root"')

            .with_directory('profiles/default')
            .with_zcml_node('genericsetup:registerProfile',
                            name='default',
                            title='other.package:default',
                            directory='profiles/default',
                            provides='Products.GenericSetup.interfaces.EXTENSION')

            .with_directory('upgrades')
            .with_file('upgrades/__init__.py', 'PACKAGE = "upgrades package"')
            .with_zcml_include('ftw.upgrade', file='meta.zcml')
            .with_zcml_node('upgrade-step:directory',
                            profile='other.package:default',
                            directory='upgrades'))

        with create(package_builder).zcml_loaded(self.layer['configurationContext']):
            import other.package
            self.assertEquals('package root', other.package.PACKAGE)

    def test_profile_must_be_registed_before_registering_upgrade_directory(self):
        package_builder = (Builder('python package')
                           .named('other.package')
                           .at_path(self.layer['temp_directory'])
                           .with_zcml_include('ftw.upgrade', file='meta.zcml')
                           .with_zcml_node('upgrade-step:directory',
                                           profile='other.package:default',
                                           directory='.'))

        with create(package_builder) as package:
            with self.assertRaises(ConfigurationExecutionError) as cm:
                package.load_zcml(self.layer['configurationContext'])

        self.assertEqual(
            "<class 'ftw.upgrade.exceptions.UpgradeStepConfigurationError'>: "
            'The profile "other.package:default" needs to be registered'
            ' before registering its upgrade step directory.',
            str(cm.exception).splitlines()[0])

    def test_profile_version_is_set_to_latest_profile_version(self):
        self.profile.with_upgrade(Builder('ftw upgrade step').to(datetime(2011, 1, 1, 8)))
        self.profile.with_upgrade(Builder('ftw upgrade step').to(datetime(2011, 2, 2, 8)))

        with self.package_created() as package:
            profile_path = package.package_path.joinpath('profiles', 'default')
            self.assert_profile(
                {'id': u'the.package:default',
                 'title': u'the.package',
                 'description': u'',
                 'path': profile_path,
                 'version': '20110202080000',
                 'product': 'the.package',
                 'type': EXTENSION,
                 'for': None})

    def test_profile_version_is_set_to_latest_old_school_profile_version(self):
        self.profile.with_upgrade(Builder('plone upgrade step')
                                  .upgrading('1000', to='1001')
                                  .titled('Register foo utility.'))
        self.profile.with_upgrade(Builder('ftw upgrade step')
                                  .to(datetime(2011, 2, 2, 8)))

        package = create(self.package)
        # Remove upgrade-step directory upgrade in order to have the
        # manually created upgrade step as last version
        # but still declaring an upgrade-step:directory:
        package.package_path.joinpath(
            'upgrades', '20110202080000_upgrade').rmtree()

        profile_path = package.package_path.joinpath('profiles', 'default')
        self.assertNotIn('<version',
                         profile_path.joinpath('metadata.xml').text())

        with package.zcml_loaded(self.layer['configurationContext']):
            from ftw.upgrade.directory.zcml import find_start_version
            find_start_version(u'the.package:default')
            self.assert_profile(
                {'id': u'the.package:default',
                 'title': u'the.package',
                 'description': u'',
                 'path': str(profile_path),
                 'version': '1001',
                 'product': 'the.package',
                 'type': EXTENSION,
                 'for': None})

    def test_version_set_to_default_when_no_upgrades_defined(self):
        upgrades = self.package.package.get_subpackage('upgrades')
        upgrades.with_zcml_include('ftw.upgrade', file='meta.zcml')
        upgrades.with_zcml_node('upgrade-step:directory',
                                profile='the.package:default',
                                directory='.')

        with self.package_created() as package:
            profile_path = package.package_path.joinpath('profiles', 'default')
            self.assert_profile(
                {'id': u'the.package:default',
                 'title': u'the.package',
                 'description': u'',
                 'path': profile_path,
                 'version': u'10000000000000',
                 'product': 'the.package',
                 'type': EXTENSION,
                 'for': None})

    def test_profile_must_not_have_a_metadata_version_defined(self):
        self.profile.with_fs_version('1000')
        self.profile.with_upgrade(Builder('ftw upgrade step').to(datetime(2011, 1, 1, 8)))

        with create(self.package) as package:
            with self.assertRaises(ConfigurationExecutionError) as cm:
                package.load_zcml(self.layer['configurationContext'])

        self.assertEqual(
            "<class 'ftw.upgrade.exceptions.UpgradeStepConfigurationError'>: "
            'Registering an upgrades directory for "the.package:default" requires'
            ' this profile to not define a version in its metadata.xml.'
            ' The version is automatically set to the latest upgrade.',
            str(cm.exception).splitlines()[0])

    def assert_upgrades(self, expected):
        upgrades = self.portal_setup.listUpgrades('the.package:default')
        got = [dict((key, value) for (key, value) in step.items()
                    if key in ('source', 'dest', 'title'))
               for step in upgrades]
        self.maxDiff = None
        self.assertItemsEqual(expected, got)

    def assert_profile(self, expected):
        self.assertTrue(
            self.portal_setup.profileExists(expected['id']),
            'Profile "{0}" does not exist. Profiles: {1}'.format(
                expected['id'],
                [profile['id'] for profile in self.portal_setup.listProfileInfo()]))

        got = self.portal_setup.getProfileInfo(expected['id']).copy()

        # Ignore pre_handler and post_handler, only available in Plone >= 4.3.8
        got.pop('pre_handler', None)
        got.pop('post_handler', None)

        self.maxDiff = None
        self.assertDictEqual(expected, got)
