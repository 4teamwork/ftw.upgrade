from Products.CMFCore.utils import getToolByName
from ftw.upgrade import UpgradeStep
from ftw.upgrade.interfaces import IUpgradeStep
from ftw.upgrade.testing import FTW_UPGRADE_FUNCTIONAL_TESTING
from unittest2 import TestCase
from zope.interface.verify import verifyClass


class TestUpgradeStep(TestCase):

    layer = FTW_UPGRADE_FUNCTIONAL_TESTING

    def setUp(self):
        super(TestUpgradeStep, self).setUp()
        self.portal = self.layer['portal']
        self.portal_setup = getToolByName(self.portal, 'portal_setup')

    def test_implements_interface(self):
        verifyClass(IUpgradeStep, UpgradeStep)

    def test_upgrade_classmethod(self):
        with self.assertRaises(NotImplementedError):
            UpgradeStep.upgrade(self.portal_setup)

    def test_portal_setup_attribute(self):
        testcase = self

        class Step(UpgradeStep):
            def __call__(self):
                testcase.assertEqual(self.portal_setup, testcase.portal_setup)

        Step.upgrade(self.portal_setup)

    def test_portal_attribute(self):
        testcase = self

        class Step(UpgradeStep):
            def __call__(self):
                testcase.assertEqual(self.portal, testcase.portal)

        Step.upgrade(self.portal_setup)

    def test_getToolByName(self):
        actions_tool = getToolByName(self.portal, 'portal_actions')
        testcase = self

        class Step(UpgradeStep):
            def __call__(self):
                testcase.assertEqual(
                    self.getToolByName('portal_actions'),
                    actions_tool)

        Step.upgrade(self.portal_setup)

    def test_catalog_rebuild_index(self):
        testcase = self

        class Step(UpgradeStep):
            def __call__(self):
                ctool = self.getToolByName('portal_catalog')
                name = 'getExcludeFromNav'

                self.catalog_add_index(name, 'BooleanIndex')
                testcase.assertEqual(len(ctool._catalog.getIndex(name)), 0)
                self.catalog_rebuild_index(name)
                testcase.assertEqual(len(ctool._catalog.getIndex(name)), 1)

        self.portal.invokeFactory('Folder', 'rebuild-index-test-obj',
                                  excludeFromNav=True)
        Step.upgrade(self.portal_setup)
        self.portal.manage_delObjects(['rebuild-index-test-obj'])

    def test_catalog_has_index(self):
        testcase = self

        class Step(UpgradeStep):
            def __call__(self):
                testcase.assertTrue(self.catalog_has_index('sortable_title'))
                testcase.assertFalse(self.catalog_has_index('foo'))

        Step.upgrade(self.portal_setup)

    def test_catalog_add_and_remove_indexes(self):
        testcase = self

        class Step(UpgradeStep):
            def __call__(self):
                testcase.assertFalse(self.catalog_has_index('foo'))
                self.catalog_add_index('foo', 'FieldIndex')
                testcase.assertTrue(self.catalog_has_index('foo'))
                self.catalog_remove_index('foo')
                testcase.assertFalse(self.catalog_has_index('foo'))

        Step.upgrade(self.portal_setup)

    def test_actions_remove_action(self):
        atool = getToolByName(self.portal, 'portal_actions')
        self.assertIn('rss', atool.get('document_actions'))
        testcase = self

        class Step(UpgradeStep):
            def __call__(self):
                testcase.assertTrue(self.actions_remove_action(
                        'document_actions', 'rss'))
                testcase.assertFalse(self.actions_remove_action(
                        'document_actions', 'rss'))

        Step.upgrade(self.portal_setup)
        self.assertNotIn('rss', atool.get('document_actions'))

    def test_actions_remove_type_action(self):
        testcase = self

        class Step(UpgradeStep):
            def event_has_action(self, actionid):
                ttool = self.getToolByName('portal_types')
                fti = ttool.get('Event')

                for action in fti._actions:
                    if action.id == actionid:
                        return True

                return False

            def __call__(self):
                testcase.assertTrue(self.event_has_action('history'))
                testcase.assertTrue(
                    self.actions_remove_type_action('Event', 'history'))
                testcase.assertFalse(self.event_has_action('history'))

        Step.upgrade(self.portal_setup)

    def test_set_property(self):
        testcase = self

        class Step(UpgradeStep):
            def __call__(self):
                testcase.assertFalse(self.portal.hasProperty('foo'))

                self.set_property(self.portal, 'foo', 'bar')
                testcase.assertTrue(self.portal.hasProperty('foo'))
                testcase.assertEqual(self.portal.getProperty('foo'), 'bar')

                self.set_property(self.portal, 'foo', 'baz')
                testcase.assertEqual(self.portal.getProperty('foo'), 'baz')

        Step.upgrade(self.portal_setup)

    def test_add_lines_to_property(self):
        testcase = self

        class Step(UpgradeStep):
            def __call__(self):
                key = 'foo-lines'

                testcase.assertFalse(self.portal.hasProperty(key))

                self.add_lines_to_property(self.portal, key, 'foo')
                testcase.assertEqual(self.portal.getProperty(key),
                                     ('foo',))

                self.add_lines_to_property(self.portal, key, ['bar'])
                testcase.assertEqual(self.portal.getProperty(key),
                                     ('foo', 'bar'))

                self.add_lines_to_property(self.portal, key, 'baz')
                testcase.assertEqual(self.portal.getProperty(key),
                                     ('foo', 'bar', 'baz'))

                self.set_property(self.portal, key, ('foo'))
                testcase.assertEqual(self.portal.getProperty(key),
                                     ('foo',))

                self.add_lines_to_property(self.portal, key, ['bar'])
                testcase.assertEqual(self.portal.getProperty(key),
                                     ('foo', 'bar'))

                self.add_lines_to_property(self.portal, key, ('baz',))
                testcase.assertEqual(self.portal.getProperty(key),
                                     ('foo', 'bar', 'baz'))

                self.portal.manage_delProperties([key])
                self.add_lines_to_property(self.portal, key, ['foo', 'bar'])
                testcase.assertEqual(self.portal.getProperty(key),
                                     ('foo', 'bar'))

        Step.upgrade(self.portal_setup)

    def test_setup_install_profile(self):
        testcase = self

        class Step(UpgradeStep):
            def __call__(self):
                testcase.assertFalse(self.catalog_has_index('excludeFromNav'))
                self.setup_install_profile(
                    'profile-ftw.upgrade.tests.profiles:navigation-index')
                testcase.assertTrue(self.catalog_has_index('excludeFromNav'))

                self.catalog_remove_index('excludeFromNav')
                testcase.assertFalse(self.catalog_has_index('excludeFromNav'))
                self.setup_install_profile(
                    'profile-ftw.upgrade.tests.profiles:navigation-index',
                    ['catalog'])
                testcase.assertTrue(self.catalog_has_index('excludeFromNav'))

        Step.upgrade(self.portal_setup)

    def test_purge_resource_registries(self):
        testcase = self

        class Step(UpgradeStep):
            def __call__(self):
                jstool = self.getToolByName('portal_javascripts')
                csstool = self.getToolByName('portal_css')
                ksstool = self.getToolByName('portal_kss')

                testcase.assertNotEqual(
                    len(jstool.concatenatedresources), 0)
                testcase.assertNotEqual(
                    len(csstool.concatenatedresources), 0)
                testcase.assertNotEqual(
                    len(ksstool.concatenatedresources), 0)

                self.purge_resource_registries()

                testcase.assertEqual(
                    len(jstool.concatenatedresources), 0)
                testcase.assertEqual(
                    len(csstool.concatenatedresources), 0)
                testcase.assertEqual(
                    len(ksstool.concatenatedresources), 0)

        Step.upgrade(self.portal_setup)
