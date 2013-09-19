from DateTime import DateTime
from Products.CMFCore.utils import getToolByName
from StringIO import StringIO
from ftw.builder import Builder
from ftw.builder import create
from ftw.upgrade import UpgradeStep
from ftw.upgrade.interfaces import IUpgradeStep
from ftw.upgrade.testing import FTW_UPGRADE_FUNCTIONAL_TESTING
from plone.browserlayer.utils import register_layer
from unittest2 import TestCase
from zope.interface import Interface
from zope.interface.verify import verifyClass
import logging


class IMyProductLayer(Interface):
    """Dummy class used in test_remove_broken_browserlayer()
    """


class TestUpgradeStep(TestCase):

    layer = FTW_UPGRADE_FUNCTIONAL_TESTING

    def setUp(self):
        super(TestUpgradeStep, self).setUp()
        self.portal = self.layer['portal']
        self.portal_setup = getToolByName(self.portal, 'portal_setup')

        self.log = StringIO()
        self.logger = logging.getLogger('ftw.upgrade')
        self.logger.setLevel(logging.DEBUG)

        handler = logging.StreamHandler(self.log)
        self.logger.addHandler(handler)

    def test_implements_interface(self):
        verifyClass(IUpgradeStep, UpgradeStep)

    def test_upgrade_classmethod(self):
        with self.assertRaises(NotImplementedError):
            UpgradeStep(self.portal_setup)

    def test_portal_setup_attribute(self):
        testcase = self

        class Step(UpgradeStep):
            def __call__(self):
                testcase.assertEqual(testcase.portal_setup, self.portal_setup)

        Step(self.portal_setup)

    def test_portal_attribute(self):
        testcase = self

        class Step(UpgradeStep):
            def __call__(self):
                testcase.assertEqual(testcase.portal, self.portal)

        Step(self.portal_setup)

    def test_getToolByName(self):
        actions_tool = getToolByName(self.portal, 'portal_actions')
        testcase = self

        class Step(UpgradeStep):
            def __call__(self):
                testcase.assertEqual(
                    actions_tool,
                    self.getToolByName('portal_actions'))

        Step(self.portal_setup)

    def test_objects_method_yields_objects_with_logging(self):
        testcase = self
        create(Builder('folder').titled('Foo'))
        create(Builder('folder').titled('Bar'))
        create(Builder('folder').titled('Baz'))

        object_titles = []

        class Step(UpgradeStep):
            def __call__(self):
                for obj in self.objects({'portal_type': 'Folder'},
                                        'Log message',
                                        logger=testcase.logger):
                    object_titles.append(obj.Title())

        Step(self.portal_setup)

        self.assertEquals(set(['Foo', 'Bar', 'Baz']), set(object_titles))

        self.assertEquals(['STARTING Log message',
                           '1 of 3 (33%): Log message',
                           'DONE Log message'],
                          self.read_log())

    def test_objects_modifying_catalog_does_not_reduce_result_set(self):
        old_date = DateTime(2010, 1, 1)
        new_date = DateTime(2012, 3, 3)
        create(Builder('folder').with_modification_date(old_date))
        create(Builder('folder').with_modification_date(old_date))
        create(Builder('folder').with_modification_date(old_date))
        create(Builder('folder').with_modification_date(old_date))

        data = {'processed_folders': 0}

        class Step(UpgradeStep):
            def __call__(self):
                for obj in self.objects({'modified': old_date}, ''):
                    obj.setModificationDate(new_date)
                    obj.reindexObject(idxs=['modified'])
                    data['processed_folders'] += 1

        Step(self.portal_setup)
        self.assertEquals(
            4, data['processed_folders'],
            'Updating catalog reduced result set while iterating over it!!!')

    def test_catalog_rebuild_index(self):
        testcase = self

        class Step(UpgradeStep):
            def __call__(self):
                ctool = self.getToolByName('portal_catalog')
                name = 'getExcludeFromNav'

                self.catalog_add_index(name, 'BooleanIndex')
                testcase.assertEqual(0, len(ctool._catalog.getIndex(name)))
                self.catalog_rebuild_index(name)
                testcase.assertEqual(1, len(ctool._catalog.getIndex(name)))

        create(Builder('folder')
               .titled('Rebuild Index Test Obj')
               .having(excludeFromNav=True))

        Step(self.portal_setup)

    def test_catalog_reindex_objects(self):
        testcase = self
        create(Builder('folder'))

        class Step(UpgradeStep):
            def __call__(self):
                ctool = self.getToolByName('portal_catalog')
                name = 'getExcludeFromNav'

                self.catalog_add_index(name, 'BooleanIndex')
                testcase.assertEqual(0, len(ctool._catalog.getIndex(name)))

                self.catalog_reindex_objects({'portal_type': 'Folder'})

                self.catalog_rebuild_index(name)
                testcase.assertEqual(1, len(ctool._catalog.getIndex(name)))

        Step(self.portal_setup)

    def test_catalog_reindex_objects_keeps_modification_date(self):
        testcase = self
        folder = create(Builder('folder'))

        modification_date = DateTime('2010/12/31')
        folder.setModificationDate(modification_date)
        folder.reindexObject(idxs=['modified'])

        class Step(UpgradeStep):
            def __call__(self):

                brain = self.catalog_unrestricted_search(
                    {'UID': folder.UID()})[0]
                testcase.assertEquals(modification_date, brain.modified)

                self.catalog_reindex_objects({})

                brain = self.catalog_unrestricted_search(
                    {'UID': folder.UID()})[0]
                testcase.assertEquals(modification_date, brain.modified)

        Step(self.portal_setup)

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
        folder = create(Builder('folder'))
        create(Builder('document').within(folder))

        folder_path = '/'.join(folder.getPhysicalPath())

        class Step(UpgradeStep):
            def __call__(self):
                query = {'path': folder_path,
                         'portal_type': 'Document'}
                brains = self.catalog_unrestricted_search(query)

                brain = brains[0]
                testcase.assertEqual(
                    'ImplicitAcquisitionWrapper',
                    type(brain).__name__)

                obj = self.catalog_unrestricted_get_object(brain)
                testcase.assertEqual(
                    'ImplicitAcquisitionWrapper',
                    type(obj).__name__)

        Step(self.portal_setup)

    def test_catalog_unrestricted_search(self):
        testcase = self

        folder = create(Builder('folder'))
        create(Builder('document').titled('Page One').within(folder))
        create(Builder('document').titled('Page Two').within(folder))

        folder_path = '/'.join(folder.getPhysicalPath())

        class Step(UpgradeStep):
            def __call__(self):
                query = {'path': folder_path,
                         'portal_type': 'Document'}
                brains = self.catalog_unrestricted_search(query)

                testcase.assertEqual(2, len(brains))
                testcase.assertEqual(['page-one', 'page-two'],
                                     [brain.id for brain in brains])
                testcase.assertEqual('ImplicitAcquisitionWrapper',
                                     type(brains[0]).__name__)

                objects = self.catalog_unrestricted_search(
                    query, full_objects=True)
                testcase.assertEqual(2, len(objects))
                objects = list(objects)
                testcase.assertEqual(['page-one', 'page-two'],
                                     [obj.id for obj in objects])
                testcase.assertEqual('ImplicitAcquisitionWrapper',
                                     type(objects[0]).__name__)

        Step(self.portal_setup)

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

    def test_actions_add_type_action(self):
        testcase = self

        class Step(UpgradeStep):
            def get_event_action(self, actionid):
                ttool = self.getToolByName('portal_types')
                fti = ttool.get('Event')

                for action in fti._actions:
                    if action.id == actionid:
                        return action

            def get_action_ids(self):
                ttool = self.getToolByName('portal_types')
                fti = ttool.get('Event')

                return [action.id for action in fti._actions]

            def __call__(self):
                testcase.assertEquals(
                    None, self.get_event_action('additional'))
                testcase.assertEquals(
                    ['view', 'edit', 'history', 'external_edit'],
                    self.get_action_ids())

                self.actions_add_type_action(
                    'Event', 'history', action_id='additional', title='Additional',
                    action='string:#', permissions=('View', ))

                testcase.assertEquals(
                    ['view', 'edit', 'history', 'additional', 'external_edit'],
                    self.get_action_ids())

                action = self.get_event_action('additional')
                testcase.assertEquals('Additional', action.title)
                testcase.assertEquals('string:#', action.action.text)

        Step(self.portal_setup)

    def test_set_property(self):
        testcase = self

        class Step(UpgradeStep):
            def __call__(self):
                testcase.assertFalse(self.portal.hasProperty('foo'))

                self.set_property(self.portal, 'foo', 'bar')
                testcase.assertTrue(self.portal.hasProperty('foo'))
                testcase.assertEqual('bar', self.portal.getProperty('foo'))

                self.set_property(self.portal, 'foo', 'baz')
                testcase.assertEqual('baz', self.portal.getProperty('foo'))

        Step(self.portal_setup)

    def test_add_lines_to_property(self):
        testcase = self

        class Step(UpgradeStep):
            def __call__(self):
                key = 'foo-lines'

                testcase.assertFalse(self.portal.hasProperty(key))

                self.add_lines_to_property(self.portal, key, 'foo')
                testcase.assertEqual(('foo',),
                                     self.portal.getProperty(key))

                self.add_lines_to_property(self.portal, key, ['bar'])
                testcase.assertEqual(('foo', 'bar'),
                                     self.portal.getProperty(key))

                self.add_lines_to_property(self.portal, key, 'baz')
                testcase.assertEqual(('foo', 'bar', 'baz'),
                                     self.portal.getProperty(key))

                self.set_property(self.portal, key, ('foo'))
                testcase.assertEqual(('foo',),
                                     self.portal.getProperty(key))

                self.add_lines_to_property(self.portal, key, ['bar'])
                testcase.assertEqual(('foo', 'bar'),
                                     self.portal.getProperty(key))

                self.add_lines_to_property(self.portal, key, ('baz',))
                testcase.assertEqual(('foo', 'bar', 'baz'),
                                     self.portal.getProperty(key))

                self.portal.manage_delProperties([key])
                self.add_lines_to_property(self.portal, key, ['foo', 'bar'])
                testcase.assertEqual(('foo', 'bar'),
                                     self.portal.getProperty(key))

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

        folder = create(Builder('folder'))
        subfolder = create(Builder('folder').within(folder))


        class Step(UpgradeStep):
            def __call__(self):
                self.migrate_class(subfolder, ATBTreeFolder)

        self.assertEqual('ATFolder', subfolder.__class__.__name__)
        Step(self.portal_setup)
        self.assertEqual('ATBTreeFolder', subfolder.__class__.__name__)

    def test_remove_broken_browserlayer(self):
        # TODO: Currently, this test doesn't really test that the removal
        # works, it only checks that the Step method can be called without
        # causing problems.

        register_layer(IMyProductLayer, 'my.product')

        class Step(UpgradeStep):
            def __call__(self):
                self.remove_broken_browserlayer('my.product',
                                                'IMyProductLayer')
        Step(self.portal_setup)

    def test_update_security_removes_roles_unmanaged_by_workflow(self):
        self.set_workflow_chain(for_type='Folder',
                                to_workflow='plone_workflow')
        folder = create(Builder('folder'))

        self.assert_permission_not_acquired('View', folder)
        self.assert_permission_not_acquired('Modify portal content', folder)
        self.assert_permission_acquired('List folder contents', folder)

        folder.manage_permission('Modify portal content', roles=[],
                                 acquire=True)
        folder.manage_permission('List folder contents', roles=[],
                                 acquire=False)

        self.assert_permission_not_acquired('View', folder)
        self.assert_permission_acquired('Modify portal content', folder)
        self.assert_permission_not_acquired('List folder contents', folder)

        class Step(UpgradeStep):
            def __call__(self):
                self.update_security(folder)
        Step(self.portal_setup)

        self.assert_permission_not_acquired('View', folder)
        self.assert_permission_not_acquired('Modify portal content', folder)
        self.assert_permission_acquired('List folder contents', folder)

    def test_update_security_reindexes_security_indexes(self):
        self.set_workflow_chain(for_type='Folder',
                                to_workflow='simple_publication_workflow')
        folder = create(Builder('folder')
                        .in_state('published'))

        self.assertEquals(['Anonymous'],
                          self.get_allowed_roles_and_users_for(folder))
        folder.reindexObjectSecurity()

        folder.manage_permission('View', roles=['Reader'], acquire=False)
        folder.reindexObjectSecurity()

        self.assertEquals(['Reader'],
                          self.get_allowed_roles_and_users_for(folder))

        class Step(UpgradeStep):
            def __call__(self):
                self.update_security(folder)
        Step(self.portal_setup)

        self.assertEquals(['Anonymous'],
                          self.get_allowed_roles_and_users_for(folder))

    def test_update_security_without_reindexing_security(self):
        self.set_workflow_chain(for_type='Folder',
                                to_workflow='simple_publication_workflow')
        folder = create(Builder('folder')
                        .in_state('published'))

        self.assertEquals(['Anonymous'],
                          self.get_allowed_roles_and_users_for(folder))

        folder.manage_permission('View', roles=['Reader'], acquire=False)
        folder.reindexObjectSecurity()

        self.assertEquals(['Reader'],
                          self.get_allowed_roles_and_users_for(folder))

        class Step(UpgradeStep):
            def __call__(self):
                self.update_security(folder, reindex_security=False)
        Step(self.portal_setup)

        self.assertEquals(['Reader'],
                          self.get_allowed_roles_and_users_for(folder))

    def test_update_workflow_security_updates_security(self):
        self.set_workflow_chain(for_type='Folder',
                                to_workflow='plone_workflow')
        folder = create(Builder('folder'))
        self.assert_permission_not_acquired('Modify portal content', folder)
        folder.manage_permission('Modify portal content', roles=[],
                                 acquire=True)
        self.assert_permission_acquired('Modify portal content', folder)

        class Step(UpgradeStep):
            def __call__(self):
                self.update_workflow_security(['plone_workflow'])
        Step(self.portal_setup)

        self.assert_permission_not_acquired('Modify portal content', folder)

    def test_update_workflow_security_reindexes_security(self):
        self.set_workflow_chain(for_type='Folder',
                                to_workflow='plone_workflow')
        folder = create(Builder('folder').in_state('published'))

        folder.manage_permission('View', roles=['Reader'], acquire=False)
        folder.reindexObjectSecurity()
        self.assertEquals(['Reader'],
                          self.get_allowed_roles_and_users_for(folder))

        class Step(UpgradeStep):
            def __call__(self):
                self.update_workflow_security(
                    ['plone_workflow'], reindex_security=False)
        Step(self.portal_setup)

        self.assertEquals(['Reader'],
                          self.get_allowed_roles_and_users_for(folder))

        class Step(UpgradeStep):
            def __call__(self):
                self.update_workflow_security(
                    ['plone_workflow'], reindex_security=True)
        Step(self.portal_setup)

        self.assertEquals(['Anonymous'],
                          self.get_allowed_roles_and_users_for(folder))


    def test_update_workflow_security_expects_list_of_workflows(self):
        class Step(UpgradeStep):
            def __call__(self):
                self.update_workflow_security('foo')

        with self.assertRaises(ValueError) as cm:
            Step(self.portal_setup)

        self.assertEquals('"workflows" must be a list of workflow names.',
                          str(cm.exception))

    def set_workflow_chain(self, for_type, to_workflow):
        wftool = getToolByName(self.portal, 'portal_workflow')
        wftool.setChainForPortalTypes((for_type,),
                                      (to_workflow,))

    def assert_permission_acquired(self, permission, obj):
        not_acquired_permissions = self.get_not_acquired_permissions_of(obj)

        self.assertNotIn(
            permission, not_acquired_permissions,
            'Expected permission "%s" to be acquired on %s' % (
                permission, str(obj)))

    def assert_permission_not_acquired(self, permission, obj):
        not_acquired_permissions = self.get_not_acquired_permissions_of(obj)

        self.assertIn(
            permission, not_acquired_permissions,
            'Expected permission "%s" to NOT be acquired on %s' % (
                permission, str(obj)))

    def get_not_acquired_permissions_of(self, obj):
        acquired_permissions = filter(
            lambda item: not item.get('acquire'),
            obj.permission_settings())

        return map(lambda item: item.get('name'), acquired_permissions)

    def get_allowed_roles_and_users_for(self, obj):
        catalog = getToolByName(self.portal, 'portal_catalog')
        path = '/'.join(obj.getPhysicalPath())
        rid = catalog.getrid(path)
        index_data = catalog.getIndexDataForRID(rid)
        return index_data.get('allowedRolesAndUsers')

    def read_log(self):
        self.log.seek(0)
        return self.log.read().strip().split('\n')
