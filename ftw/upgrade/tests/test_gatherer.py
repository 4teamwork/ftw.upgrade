from ftw.testing import MockTestCase
from unittest2 import TestCase
from ftw.upgrade import UpgradeStep
from ftw.upgrade.directory.wrapper import wrap_upgrade_step
from ftw.upgrade.exceptions import CyclicDependencies
from ftw.upgrade.gatherer import extend_auto_upgrades_with_human_formatted_date_version
from ftw.upgrade.gatherer import UpgradeInformationGatherer
from ftw.upgrade.interfaces import IUpgradeInformationGatherer
from ftw.upgrade.interfaces import IUpgradeStepRecorder
from ftw.upgrade.testing import ZCML_LAYER
from mocker import ANY
from Products.CMFPlone.interfaces import IPloneSiteRoot
from Products.GenericSetup.interfaces import ISetupTool
from Products.GenericSetup.upgrade import UpgradeStep as GenericSetupUpgradeStep
from random import random
from zope.annotation import IAttributeAnnotatable
from zope.component import getMultiAdapter
from zope.component import queryAdapter
from zope.interface.verify import verifyClass


def generate_id():
    """Generates a random ten digit integer ID. Does not return the
    same value twice.
    """

    key = '__id_auto_increment__'
    if key not in globals():
        globals()[key] = set()

    while True:
        id_ = int(random() * 10 ** 10)
        if id_ not in globals()[key]:
            globals()[key].add(id_)
            return id_


def find_where(iterable, properties):
    """Looks through `iterable` and returns the first the value that matches
    all of the key-value pairs listed in `properties`.
    """
    for item in iterable:
        if all(item[key] == value for key, value in properties.items()):
            return item


def simplify_data(data, keep_order=False, profile_only=False,
                  with_orphans=False):
    """Simplifies the get_upgrades return value for easy comparison.
    """

    if keep_order:
        simple_data = []
    else:
        simple_data = {}

    for profile in data:
        proposed = []
        done = []
        orphans = []

        if profile_only:
            assert keep_order
            simple_data.append(profile['id'])
            continue

        profile_result = {'proposed': proposed, 'done': done}
        if with_orphans:
            profile_result['orphans'] = orphans

        if keep_order:
            simple_data.append(
                [profile['id'], profile_result])
        else:
            simple_data[profile['id']] = profile_result

        for upgrade in profile['upgrades']:
            if upgrade['proposed']:
                proposed.append(upgrade['title'])
            else:
                done.append(upgrade['title'])
            if upgrade['orphan']:
                orphans.append(upgrade['title'])

    return simple_data


class TestUpgradeInformationGatherer(MockTestCase):

    layer = ZCML_LAYER

    def setUp(self):
        super(TestUpgradeInformationGatherer, self).setUp()
        self.portal = self.providing_stub([IPloneSiteRoot, IAttributeAnnotatable])
        self.setup_tool = self.providing_stub(ISetupTool)
        self.quickinstaller_tool = self.stub()
        self._profiles = {}
        self._installed = set()
        self._upgrades = {}
        self._installed_products = []
        self._installable_products = []

        self.expect(self.setup_tool.portal_quickinstaller).result(
            self.quickinstaller_tool)

        self.expect(self.setup_tool.portal_url.getPortalObject()).result(self.portal)

        self.expect(self.setup_tool.listProfilesWithUpgrades()).call(
            lambda: [key for key, value in self._profiles.items()
                     if key in self._upgrades])

        self.expect(self.setup_tool.listProfileInfo()).call(
            lambda: self._profiles.values())

        self.expect(self.setup_tool.getProfileInfo(ANY)).call(
            lambda id_: id_ in self._profiles and self._profiles[id_])

        self.expect(self.setup_tool.listUpgrades(ANY)).call(
            lambda id_: id_ in self._upgrades and
            [u for u in self._upgrades[id_] if not u['done']] or [])

        self.expect(self.setup_tool.listUpgrades(ANY, show_old=True)).call(
            lambda id_, show_old: id_ in self._upgrades and
            self._upgrades[id_] or [])

        self.expect(self.setup_tool.getLastVersionForProfile(ANY)).call(
            lambda id_: (id_ in self._profiles and
                         id_ in self._installed and
                         self._profiles[id_]['db_version']) or 'unknown')

        self.expect(self.quickinstaller_tool.isProductInstalled(ANY)).call(
            lambda product: product in self._installed_products)

        self.expect(self.quickinstaller_tool.isProductInstallable(ANY)).call(
            lambda product: product in self._installable_products)

    def tearDown(self):
        super(TestUpgradeInformationGatherer, self).tearDown()
        self.setup_tool = None
        self._profiles = None
        self._installed = None
        self._upgrades = None

    def mock_profile(self, profileid, version, title=None,
                     db_version=None, installed=True,
                     product_uninstalled=False,
                     product_installable=True,
                     dependencies=None):
        product = profileid.split(':')[0]

        data = {
            'id': profileid,
            'product': product,
            'title': title or product,
            'version': version,
            'db_version': db_version or version,
            'description': '',
            'for': None,
            'type': 2,
            'path': None,
            'dependencies': dependencies,
            }
        self._profiles[profileid] = data

        if installed:
            self._installed.add(profileid)
            if not product_uninstalled:
                self._installed_products.append(product)

        if product_installable:
            self._installable_products.append(product)

    def mock_upgrade(self, profileid, source, dest, title='',
                     auto_discovered=False):
        db_version = self._profiles[profileid]['db_version']
        not_done = dest.split('.') > db_version.split('.')

        handler = None
        if auto_discovered:
            # Act as discovered with directory scan
            handler = wrap_upgrade_step(
                handler=UpgradeStep,
                upgrade_profile='profile-{0}-upgrade-{1}'.format(profileid, dest),
                base_profile='profile-{0}'.format(profileid),
                target_version=dest)

        data = {'description': None,
                'proposed': not_done,
                'done': not not_done,
                'source': source.split('.'),
                'ssource': source,
                'dest': dest.split('.'),
                'sdest': dest,
                'step': GenericSetupUpgradeStep(title=title,
                                                profile=profileid,
                                                source=source,
                                                dest=dest,
                                                desc=None,
                                                handler=handler),
                'title': title,
                'haspath': dest.split('.'),
                'sortkey': 0,
                'id': generate_id()
                }

        if profileid not in self._upgrades:
            self._upgrades[profileid] = []
        self._upgrades[profileid].append(data)

    def mock_quickinstaller_product(self, product, installed=True):
        pass

    def test_component_is_registered(self):
        self.replay()
        gatherer = queryAdapter(self.setup_tool, IUpgradeInformationGatherer)
        self.assertNotEqual(None, gatherer)

    def test_implements_interface(self):
        self.replay()
        verifyClass(IUpgradeInformationGatherer, UpgradeInformationGatherer)

    def test_get_upgrades_groups_by_profile(self):
        self.mock_profile('foo:default', '1.2', db_version='1.0')
        self.mock_upgrade('foo:default', '1.0', '1.1', 'foo1')
        self.mock_upgrade('foo:default', '1.1', '1.2', 'foo2')

        self.mock_profile('bar:default', '1.1', db_version='1.0')
        self.mock_upgrade('bar:default', '1.0', '1.1', 'bar1')
        self.replay()

        gatherer = queryAdapter(self.setup_tool, IUpgradeInformationGatherer)
        data = gatherer.get_upgrades()
        self.assertNotEqual([], data)

        self.assertIn('foo2', str(self.setup_tool.listUpgrades(
                    'foo:default', show_old=True)))

        simple = simplify_data(data)
        self.assertEqual(
            {'foo:default': {
                    'proposed': ['foo1', 'foo2'],
                    'done': []},
             'bar:default': {
                    'proposed': ['bar1'],
                    'done': []}},
            simple)

    def test_get_upgrades_proposed(self):
        self.mock_profile('foo:default', '1.2', db_version='1.1')
        self.mock_upgrade('foo:default', '1.0', '1.1', 'foo1')  # done
        self.mock_upgrade('foo:default', '1.1', '1.2', 'foo2')  # proposed

        self.mock_profile('bar:default', '1.1')
        self.mock_upgrade('bar:default', '1.0', '1.1', 'bar1')  # done

        self.mock_profile('baz:default', '1.1')  # no upgrades
        self.replay()

        gatherer = queryAdapter(self.setup_tool, IUpgradeInformationGatherer)
        data = gatherer.get_upgrades()
        self.assertNotEqual([], data)

        simple = simplify_data(data)
        self.assertEqual(
            {'foo:default': {
                    'proposed': ['foo2'],
                    'done': ['foo1']},
             'bar:default': {
                    'proposed': [],
                    'done': ['bar1']}},
            simple)

    def test_orphane_upgrades_are_marked(self):
        self.mock_profile('foo:default', '20140303080000', db_version='20140202080000')
        self.mock_upgrade('foo:default', '1000', '1001', 'foo1')
        self.mock_upgrade('foo:default', '1001', '20140101080000', 'foo2',
                          auto_discovered=True)
        self.mock_upgrade('foo:default', '20140101080000', '20140202080000', 'foo3',
                          auto_discovered=True)
        self.mock_upgrade('foo:default', '20140202080000', '20140303080000', 'foo4',
                          auto_discovered=True)
        self.replay()

        recorder = getMultiAdapter((self.portal, 'foo:default'), IUpgradeStepRecorder)
        recorder.mark_as_installed('20140202080000')

        gatherer = queryAdapter(self.setup_tool, IUpgradeInformationGatherer)
        data = gatherer.get_upgrades()
        simple = simplify_data(data, with_orphans=True)
        self.assertEqual(
            {'foo:default': {'orphans': ['foo2'],
                             'done': ['foo1', 'foo3'],
                             'proposed': ['foo2', 'foo4']}},
            simple)

    def test_human_readable_timestamp_versions_are_added_to_profiles(self):
        self.mock_profile('foo:default', '20141230104550', db_version='20141117093040')
        self.mock_upgrade('foo:default', '20141117093040', '20141230104550', 'foo3',
                          auto_discovered=True)
        self.replay()

        gatherer = queryAdapter(self.setup_tool, IUpgradeInformationGatherer)
        profile = gatherer.get_upgrades()[0]

        self.maxDiff = None
        self.assertDictContainsSubset({'db_version': '20141117093040',
                                       'formatted_db_version': '2014/11/17 09:30',
                                       'version': '20141230104550',
                                       'formatted_version': '2014/12/30 10:45'}, profile)

    def test_human_readable_timestamp_versions_are_added_to_upgrades(self):
        self.mock_profile('foo:default', '20141230104550', db_version='20141117093040')
        self.mock_upgrade('foo:default', '20141117093040', '20141230104550', 'foo3',
                          auto_discovered=True)
        self.replay()

        gatherer = queryAdapter(self.setup_tool, IUpgradeInformationGatherer)
        upgrade = gatherer.get_upgrades()[0]['upgrades'][0]

        self.assertDictContainsSubset({'ssource': '20141117093040',
                                       'fsource': '2014/11/17 09:30',
                                       'sdest': '20141230104550',
                                       'fdest': '2014/12/30 10:45'}, upgrade)

    def test_profile_with_outdated_fs_version_is_flagged(self):
        # Upgrade that leads to a higher dest version than current fs_version
        self.mock_profile('foo:default', '1.2', db_version='1.2')
        self.mock_upgrade('foo:default', '1.2', '1.3', 'foo1')

        # Destination version that wouldn't be considered 'higher' than
        # fs_version by a simple string comparision
        self.mock_profile('bar:default', '3', db_version='3')
        self.mock_upgrade('bar:default', '3', '2000', 'bar1')
        self.replay()

        gatherer = queryAdapter(self.setup_tool, IUpgradeInformationGatherer)
        upgrades = gatherer.get_upgrades()

        foo_upgrades = find_where(upgrades, {'id': 'foo:default'})
        bar_upgrades = find_where(upgrades, {'id': 'bar:default'})

        self.assertTrue(
            foo_upgrades['outdated_fs_version'],
            'Profile should be flagged as having outdated FS version')

        self.assertTrue(
            bar_upgrades['outdated_fs_version'],
            'Profile should be flagged as having outdated FS version')

        self.assertTrue(
            foo_upgrades['upgrades'][0]['outdated_fs_version'],
            'Upgrade should be flagged as outdating profile version')

        self.assertTrue(
            bar_upgrades['upgrades'][0]['outdated_fs_version'],
            'Upgrade should be flagged as outdating profile version')

    def test_profiles_with_up_to_date_fs_version_are_not_flagged(self):
        # Upgrade that leads to a destination version equal to fs_version
        self.mock_profile('foo:default', '1.2', db_version='1.1')
        self.mock_upgrade('foo:default', '1.1', '1.2', 'foo1')

        # Upgrade that leads to a destination version lower than fs_version
        self.mock_profile('bar:default', '1.2', db_version='1.0')
        self.mock_upgrade('bar:default', '1.0', '1.1', 'bar1')
        self.replay()

        gatherer = queryAdapter(self.setup_tool, IUpgradeInformationGatherer)
        upgrades = gatherer.get_upgrades()

        foo_upgrades = find_where(upgrades, {'id': 'foo:default'})
        bar_upgrades = find_where(upgrades, {'id': 'bar:default'})

        self.assertFalse(
            foo_upgrades['outdated_fs_version'],
            'Profile should NOT be flagged as having outdated FS version')

        self.assertFalse(
            bar_upgrades['outdated_fs_version'],
            'Profile should NOT be flagged as having outdated FS version')

        self.assertFalse(
            foo_upgrades['upgrades'][0]['outdated_fs_version'],
            'Upgrade should NOT be flagged as outdating profile version')

        self.assertFalse(
            bar_upgrades['upgrades'][0]['outdated_fs_version'],
            'Upgrade should NOT be flagged as outdating profile version')

    def test_profile_with_no_upgrades_is_not_listed(self):
        self.mock_profile('no-upgrades:default', '1.0',
                          title='Profile with no upgrades')
        self.mock_profile('no-upgrades2:default', ('1', '0'),
                          title='Profile with no upgrades')

        self.replay()

        gatherer = queryAdapter(self.setup_tool, IUpgradeInformationGatherer)
        self.assertEqual([], gatherer.get_upgrades())

    def test_not_installed_profile_is_not_listed(self):
        self.mock_profile('not-installed:default', '2', installed=False)
        self.mock_upgrade('not-installed:default', '1', '2', 'foo')

        self.replay()

        gatherer = queryAdapter(self.setup_tool, IUpgradeInformationGatherer)
        self.assertEqual([], gatherer.get_upgrades())

    def test_plone_profile_is_removed(self):
        self.mock_profile('Products.CMFPlone:plone', '3', db_version='2')
        self.mock_upgrade('Products.CMFPlone:plone', '2', '3', 'foo')

        self.replay()

        gatherer = queryAdapter(self.setup_tool, IUpgradeInformationGatherer)
        self.assertEqual([], gatherer.get_upgrades())

    def test_dependency_ordering(self):
        self.mock_profile('baz:default', '1.1', db_version='1.0')
        self.mock_upgrade('baz:default', '1.0', '1.1', 'baz1')

        self.mock_profile('foo:default', '1.2', db_version='1.0',
                          dependencies=['profile-bar:default',
                                        'profile-baz:default'])
        self.mock_upgrade('foo:default', '1.0', '1.1', 'foo1')

        self.mock_profile('subbar:default', '1.1', db_version='1.0',
                          dependencies=['profile-baz:default'])

        self.mock_profile('bar:default', '1.1', db_version='1.0',
                          dependencies=['profile-subbar:default',
                                        'profile-missing:default'])
        self.mock_upgrade('bar:default', '1.0', '1.1', 'bar1')

        self.replay()

        gatherer = queryAdapter(self.setup_tool, IUpgradeInformationGatherer)
        data = gatherer.get_upgrades()
        self.assertNotEqual([], data)

        simple = simplify_data(data, keep_order=True,
                               profile_only=True)
        self.assertEqual(
            ['baz:default',
             'bar:default',
             'foo:default'],
            simple)

    def test_cyclic_dependencies_raise_exception(self):
        self.mock_profile('foo:default', '1.2', db_version='1.0',
                          dependencies=['profile-bar:default'])
        self.mock_upgrade('foo:default', '1.0', '1.1', 'foo1')

        self.mock_profile('bar:default', '1.1', db_version='1.0',
                          dependencies=['profile-foo:default'])
        self.mock_upgrade('bar:default', '1.0', '1.1', 'bar1')

        self.replay()

        gatherer = queryAdapter(self.setup_tool, IUpgradeInformationGatherer)
        with self.assertRaises(CyclicDependencies) as cm:
            gatherer.get_upgrades()

        data = cm.exception.dependencies
        self.assertEqual(
            [('bar:default', 'foo:default'),
             ('foo:default', 'bar:default')],
            data)

    def test_no_longer_existing_profiles_are_silently_removed(self):
        self.mock_profile('foo:default', '1.2', db_version='1.0')
        self.mock_upgrade('foo:default', '1.0', '1.1', 'foo1')
        self.mock_upgrade('foo:default', '1.1', '1.2', 'foo2')

        self.mock_profile('removed:default', '1.1', db_version='1.0')
        self.mock_upgrade('removed:default', '1.0', '1.1', 'removed1')

        self.expect(self.setup_tool.getProfileInfo(u'removed:default')
                    ).throw(KeyError(u'removed:default'))
        self.replay()

        gatherer = queryAdapter(self.setup_tool, IUpgradeInformationGatherer)
        data = gatherer.get_upgrades()
        self.assertNotEqual([], data)

        self.assertIn('foo2', str(self.setup_tool.listUpgrades(
                    'foo:default', show_old=True)))

        simple = simplify_data(data)
        self.assertEqual(
            {'foo:default': {
                    'proposed': ['foo1', 'foo2'],
                    'done': []}},
            simple)

    def test_products_uninstalled_by_quickinstaller_are_not_listed(self):
        self.mock_profile('foo:default', '1.1', db_version='1.0', product_uninstalled=True)
        self.mock_upgrade('foo:default', '1.0', '1.1', 'foo1')
        self.replay()

        gatherer = queryAdapter(self.setup_tool, IUpgradeInformationGatherer)
        data = gatherer.get_upgrades()
        self.assertEqual([], data)

    def test_not_installable_products_are_not_checked_if_uninstalled(self):
        # Some profiles are not associated with a product.
        # Since we want those profiles to appear in manage-upgrades, we dont verify in the
        # quickinstaller that the product is installed, since it is always not installed because
        # there is no known product.
        # - Products.CMFEditions:CMFEditions
        # - Products.TinyMCE:TinyMCE
        # - plone.app.discussion:default
        # - plone.formwidget.autocomplete:default

        self.mock_profile('foo:default', '1.1', db_version='1.0', product_installable=False)
        self.mock_upgrade('foo:default', '1.0', '1.1', 'foo1')
        self.replay()

        gatherer = queryAdapter(self.setup_tool, IUpgradeInformationGatherer)
        data = gatherer.get_upgrades()
        self.assertNotEqual([], data)

        simple = simplify_data(data)
        self.assertEqual(
            {'foo:default': {
                    'proposed': ['foo1'],
                    'done': []}},
            simple)


class TestExtendAutoUpgradesWithHumanFormattedDateVersion(TestCase):

    def test_formats_timestamp_source_versions(self):
        input = {'ssource': '20141214183059',
                 'sdest': '1'}
        expected = {'ssource': '20141214183059',
                    'fsource': '2014/12/14 18:30',
                    'sdest': '1'}
        self.assertDictEqual(expected, self.format_upgrade_step(input))

    def test_formats_timestamp_dest_versions(self):
        input = {'ssource': '1',
                 'sdest': '20141214183059'}
        expected = {'ssource': '1',
                    'sdest': '20141214183059',
                    'fdest': '2014/12/14 18:30'}
        self.assertDictEqual(expected, self.format_upgrade_step(input))

    def test_does_not_format_non_timestamp_versions(self):
        input = {'ssource': '1',
                 'sdest': '2'}
        expected = {'ssource': '1',
                    'sdest': '2'}
        self.assertDictEqual(expected, self.format_upgrade_step(input))

    def test_does_not_fail_on_non_timestamp_versions_looking_like_timestamps(self):
        input = {'ssource': '10000000000000',
                 'sdest': '1'}
        expected = {'ssource': '10000000000000',
                    'sdest': '1'}
        self.assertDictEqual(expected, self.format_upgrade_step(input))

        input = {'ssource': '1',
                 'sdest': '10000000000000'}
        expected = {'ssource': '1',
                    'sdest': '10000000000000'}
        self.assertDictEqual(expected, self.format_upgrade_step(input))

    def format_upgrade_step(self, upgrade_step):
        profiles = [{'upgrades': [upgrade_step]}]
        output = extend_auto_upgrades_with_human_formatted_date_version(profiles)
        return output[0]['upgrades'][0]
