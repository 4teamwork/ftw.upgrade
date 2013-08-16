from Products.CMFCore.utils import getToolByName
from ftw.builder import Builder
from ftw.builder import create
from ftw.upgrade.helpers import update_security_for
from ftw.upgrade.testing import FTW_UPGRADE_FUNCTIONAL_TESTING
from unittest2 import TestCase


class TestUpdateSecurity(TestCase):

    layer = FTW_UPGRADE_FUNCTIONAL_TESTING

    def setUp(self):
        super(TestCase, self).setUp()
        self.portal = self.layer['portal']

    def test_removes_rules_unmanaged_by_workflow(self):
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

        update_security_for(folder)

        self.assert_permission_not_acquired('View', folder)
        self.assert_permission_not_acquired('Modify portal content', folder)
        self.assert_permission_acquired('List folder contents', folder)

    def test_reindexes_security_indexes(self):
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

        update_security_for(folder)

        self.assertEquals(['Anonymous'],
                          self.get_allowed_roles_and_users_for(folder))

    def test_without_reindexing_security(self):
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

        update_security_for(folder, reindex_security=False)

        self.assertEquals(['Reader'],
                          self.get_allowed_roles_and_users_for(folder))

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
