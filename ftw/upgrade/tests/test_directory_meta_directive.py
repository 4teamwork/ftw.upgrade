from ftw.builder import Builder
from ftw.builder import create
from ftw.upgrade.testing import ZCML_LAYER
from operator import itemgetter
from Products.CMFPlone.interfaces import IMigratingPloneSiteRoot
from Products.GenericSetup.interfaces import EXTENSION
from Products.GenericSetup.registry import _profile_registry
from Products.GenericSetup.upgrade import _upgrade_registry
from unittest2 import TestCase
import imp
import os.path
import shutil
import sys
import tempfile


class TestDirectoryMetaDirective(TestCase):

    layer = ZCML_LAYER

    def setUp(self):
        self.temp_directory = tempfile.mkdtemp('ftw.upgrade.tests')
        open(os.path.join(self.temp_directory, '__init__.py'), 'w+').close()
        self.upgrades_directory = os.path.join(self.temp_directory, 'upgrades')
        os.mkdir(self.upgrades_directory)
        open(os.path.join(self.upgrades_directory, '__init__.py'), 'w+').close()

    def tearDown(self):
        shutil.rmtree(self.temp_directory)

    def test_upgrade_steps_are_registered(self):
        create(Builder('upgrade step')
               .named('20110101080000_add_action')
               .titled('Add an action')
               .within(self.upgrades_directory))

        create(Builder('upgrade step')
               .named('20110202080000_update_action')
               .titled('Remove the action')
               .within(self.upgrades_directory))

        self.load_upgrade_step_directory_zcml()
        self.assert_upgrades([
                {'source': ('10000000000000',),
                 'dest': ('20110101080000',),
                 'title': u'Add an action'},

                {'source': ('20110101080000',),
                 'dest': ('20110202080000',),
                 'title': u'Remove the action'}])

    def test_first_source_version_is_last_regulare_upgrade_step(self):
        create(Builder('upgrade step')
               .named('20110101080000_add_action')
               .titled('Add an action')
               .within(self.upgrades_directory))

        self.load_upgrade_step_directory_zcml('''
            <genericsetup:upgradeStep
                profile="my.package:default"
                source="1"
                destination="2"
                title="Register foo utility"
                handler="ftw.upgrade.tests.upgrades.foo.register_foo_utility"
                />
            ''')

        self.assert_upgrades([
                {'source': ('1',),
                 'dest': ('2',),
                 'title': u'Register foo utility'},

                {'source': ('2',),
                 'dest': ('20110101080000',),
                 'title': u'Add an action'}])

    def test_registers_migration_generic_setup_profile_foreach_step(self):
        path = create(Builder('upgrade step')
                      .named('20110101080000_add_action')
                      .titled('Add an action')
                      .within(self.upgrades_directory))

        self.load_upgrade_step_directory_zcml()
        self.assert_profile(
            {'id': 'my.package:default-upgrade-20110101080000',
             'title': 'Upgrade my.package:default ' + \
                 'to 20110101080000: Add an action',
             'description': '',
             'path': path,
             'product': 'my.package',
             'type': EXTENSION,
             'for': IMigratingPloneSiteRoot})

    def load_upgrade_step_directory_zcml(self, additional_zcml=''):
        with open(os.path.join(self.temp_directory, 'configure.zcml'), 'w+') as f:
            f.write('''
                <configure
                    xmlns="http://namespaces.zope.org/zope"
                    xmlns:upgrade-step="http://namespaces.zope.org/ftw.upgrade"
                    xmlns:genericsetup="http://namespaces.zope.org/genericsetup"
                    i18n_domain="my.package">

                    <include package="ftw.upgrade" file="meta.zcml" />

                    {0}

                    <upgrade-step:directory
                        profile="my.package:default"
                        directory="upgrades"
                        />

                </configure>
                '''.format(additional_zcml))

        fp, pathname, description = imp.find_module('.', [self.temp_directory])
        module = imp.load_module('my.package',
                                 fp, pathname, description)
        try:
            self.layer.load_zcml_file('configure.zcml', module)
        finally:
            del sys.modules['my.package']

    def assert_upgrades(self, expected):
        upgrades = _upgrade_registry.getUpgradeStepsForProfile(
            u'my.package:default')
        got = [dict((key, value) for (key, value) in vars(step).items()
                    if key in ('source', 'dest', 'title'))
               for step in upgrades.values()]
        got.sort(key=itemgetter('dest'))

        self.maxDiff = None
        self.assertEqual(expected, got)

    def assert_profile(self, expected):
        got = _profile_registry.getProfileInfo(expected['id'])
        self.maxDiff = None
        self.assertDictEqual(expected, got)
