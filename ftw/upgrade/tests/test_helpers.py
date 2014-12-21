from ftw.builder import Builder
from ftw.builder import create
from ftw.upgrade.helpers import update_security_for
from ftw.upgrade.tests.base import WorkflowTestCase
from Products.CMFCore.utils import getToolByName


class TestUpdateSecurity(WorkflowTestCase):

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

    def get_allowed_roles_and_users_for(self, obj):
        catalog = getToolByName(self.portal, 'portal_catalog')
        path = '/'.join(obj.getPhysicalPath())
        rid = catalog.getrid(path)
        index_data = catalog.getIndexDataForRID(rid)
        return index_data.get('allowedRolesAndUsers')
