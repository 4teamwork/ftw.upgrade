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
            UpgradeStep(self.portal_setup)

    def test_portal_setup_attribute(self):
        testcase = self

        class Step(UpgradeStep):
            def __call__(self):
                testcase.assertEqual(self.portal_setup, testcase.portal_setup)

        Step(self.portal_setup)

    def test_portal_attribute(self):
        testcase = self

        class Step(UpgradeStep):
            def __call__(self):
                testcase.assertEqual(self.portal, testcase.portal)

        Step(self.portal_setup)

    def test_getToolByName(self):
        actions_tool = getToolByName(self.portal, 'portal_actions')
        testcase = self

        class Step(UpgradeStep):
            def __call__(self):
                testcase.assertEqual(
                    self.getToolByName('portal_actions'),
                    actions_tool)

        Step(self.portal_setup)

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
        Step(self.portal_setup)
        self.portal.manage_delObjects(['rebuild-index-test-obj'])

    def test_catalog_reindex_objects(self):
        testcase = self

        folder = self.portal.get(
            self.portal.invokeFactory('Folder', 'catalog-reindex-objects'))

        class Step(UpgradeStep):
            def __call__(self):
                ctool = self.getToolByName('portal_catalog')
                name = 'getExcludeFromNav'

                self.catalog_add_index(name, 'BooleanIndex')
                testcase.assertEqual(len(ctool._catalog.getIndex(name)), 0)

                self.catalog_reindex_objects({'portal_type': 'Folder'})

                self.catalog_rebuild_index(name)
                testcase.assertEqual(len(ctool._catalog.getIndex(name)), 1)

        Step(self.portal_setup)
        self.portal.manage_delObjects([folder.id])

    def test_catalog_has_index(self):
        testcase = self

        class Step(UpgradeStep):
            def __call__(self):
                testcase.assertTrue(self.catalog_has_index('sortable_title'))
                testcase.assertFalse(self.catalog_has_index('foo'))

        Step(self.portal_setup)

    def test_catalog_add_and_remove_indexes(self):
        testcase = self

        class Step(UpgradeStep):
            def __call__(self):
                testcase.assertFalse(self.catalog_has_index('foo'))
                self.catalog_add_index('foo', 'FieldIndex')
                testcase.assertTrue(self.catalog_has_index('foo'))
                self.catalog_remove_index('foo')
                testcase.assertFalse(self.catalog_has_index('foo'))

        Step(self.portal_setup)

    def test_catalog_unrestricted_get_object(self):
        testcase = self
        folder = self.portal.get(
            self.portal.invokeFactory('Folder', 'catalog-get-obj-test'))
        folder_path = '/'.join(folder.getPhysicalPath())

        folder.invokeFactory('Document', 'page-one')

        class Step(UpgradeStep):
            def __call__(self):
                query = {'path': folder_path,
                         'portal_type': 'Document'}
                brains = self.catalog_unrestricted_search(query)

                brain = brains[0]
                testcase.assertEqual(type(brain).__name__,
                                     'ImplicitAcquisitionWrapper')

                obj = self.catalog_unrestricted_get_object(brain)
                testcase.assertEqual(type(obj).__name__,
                                     'ImplicitAcquisitionWrapper')

        Step(self.portal_setup)
        self.portal.manage_delObjects([folder.id])


    def test_catalog_unrestricted_search(self):
        testcase = self
        folder = self.portal.get(
            self.portal.invokeFactory('Folder', 'catalog-search-test'))
        folder_path = '/'.join(folder.getPhysicalPath())

        folder.invokeFactory('Document', 'page-one')
        folder.invokeFactory('Document', 'page-two')

        class Step(UpgradeStep):
            def __call__(self):
                query = {'path': folder_path,
                         'portal_type': 'Document'}
                brains = self.catalog_unrestricted_search(query)

                testcase.assertEqual(len(brains), 2)
                testcase.assertEqual([brain.id for brain in brains],
                                     ['page-one', 'page-two'])
                testcase.assertEqual(type(brains[0]).__name__,
                                     'ImplicitAcquisitionWrapper')

                objects = self.catalog_unrestricted_search(
                        query, full_objects=True)
                testcase.assertEqual(len(objects), 2)
                objects = list(objects)
                testcase.assertEqual([obj.id for obj in objects],
                                     ['page-one', 'page-two'])
                testcase.assertEqual(type(objects[0]).__name__,
                                     'ImplicitAcquisitionWrapper')

        Step(self.portal_setup)
        self.portal.manage_delObjects([folder.id])

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

        Step(self.portal_setup)
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

        Step(self.portal_setup)

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

        Step(self.portal_setup)

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

        Step(self.portal_setup)

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

        Step(self.portal_setup)

    def test_migrate_class(self):
        from Products.ATContentTypes.content.folder import ATBTreeFolder

        container = self.portal.get(
            self.portal.invokeFactory('Folder', 'class-migration-test'))
        obj = container.get(container.invokeFactory('Folder', 'sub-folder'))

        class Step(UpgradeStep):
            def __call__(self):
                self.migrate_class(obj, ATBTreeFolder)

        self.assertEqual(obj.__class__.__name__, 'ATFolder')
        Step(self.portal_setup)
        self.assertEqual(obj.__class__.__name__, 'ATBTreeFolder')


        self.portal.manage_delObjects(['class-migration-test'])
