from ftw.builder import Builder
from ftw.builder import create
from ftw.upgrade.helpers import update_security_for
from ftw.upgrade.tests.base import WorkflowTestCase
from Products.CMFPlone.utils import getFSVersionTuple


ALLOWED_ROLES_AND_USERS_PERMISSION = 'View'
if getFSVersionTuple() > (5, 2):
    ALLOWED_ROLES_AND_USERS_PERMISSION = 'Access contents information'


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

        self.assertEqual(['Anonymous'],
                         self.get_allowed_roles_and_users(folder))
        folder.reindexObjectSecurity()

        folder.manage_permission(
            ALLOWED_ROLES_AND_USERS_PERMISSION, roles=['Reader'], acquire=False)
        folder.reindexObjectSecurity()

        self.assertEqual(['Reader'],
                         self.get_allowed_roles_and_users(folder))

        update_security_for(folder)

        self.assertEqual(['Anonymous'],
                         self.get_allowed_roles_and_users(folder))

    def test_without_reindexing_security(self):
        self.set_workflow_chain(for_type='Folder',
                                to_workflow='simple_publication_workflow')
        folder = create(Builder('folder')
                        .in_state('published'))

        self.assertEqual(['Anonymous'],
                         self.get_allowed_roles_and_users(folder))

        folder.manage_permission(
            ALLOWED_ROLES_AND_USERS_PERMISSION, roles=['Reader'], acquire=False)
        folder.reindexObjectSecurity()

        self.assertEqual(['Reader'],
                         self.get_allowed_roles_and_users(folder))

        update_security_for(folder, reindex_security=False)

        self.assertEqual(['Reader'],
                         self.get_allowed_roles_and_users(folder))
