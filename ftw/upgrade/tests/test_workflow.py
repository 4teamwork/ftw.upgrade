from Products.CMFCore.utils import getToolByName
from ftw.builder import Builder
from ftw.builder import create
from ftw.upgrade.testing import FTW_UPGRADE_INTEGRATION_TESTING
from ftw.upgrade.workflow import WorkflowChainUpdater
from unittest2 import TestCase


class TestWorkflowChainUpdater(TestCase):

    layer = FTW_UPGRADE_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer['portal']

    def test_changing_workflow_with_mapping(self):
        self.set_workflow_chain(for_type='Folder',
                                to_workflow='simple_publication_workflow')

        private_folder = create(Builder('folder')
                                .titled('Private Folder'))
        published_folder = create(Builder('folder')
                                  .titled('Published Folder')
                                  .in_state('published'))

        objects = [private_folder, published_folder]
        mapping = {
            ('simple_publication_workflow', 'folder_workflow'): {
                'private': 'private',
                'published': 'published'}}

        with WorkflowChainUpdater(objects, mapping):
            self.set_workflow_chain(for_type='Folder',
                                    to_workflow='simple_publication_workflow')

        self.assertReviewStates({
                private_folder: 'private',
                published_folder: 'published'})

    def test_object_security_is_updated(self):
        self.set_workflow_chain(for_type='Folder',
                                to_workflow='intranet_workflow')

        container = create(Builder('folder')
                           .titled('Container')
                           .in_state('external'))

        mapping = {
            ('intranet_workflow', 'plone_workflow'): {
                'external': 'published'}}

        with WorkflowChainUpdater([container], mapping):
            self.set_workflow_chain(for_type='Folder',
                                    to_workflow='plone_workflow')

        self.assertSecurityIsUpToDate()

    def test_object_security_is_reindexed(self):
        self.set_workflow_chain(for_type='Folder',
                                to_workflow='intranet_workflow')

        container = create(Builder('folder')
                           .titled('Container')
                           .in_state('internal'))

        self.assertIn('Member',
                      self.get_allowed_roles_and_users(for_object=container))

        mapping = {
            ('intranet_workflow', 'plone_workflow'): {
                'internal': 'published'}}

        with WorkflowChainUpdater([container], mapping):
            self.set_workflow_chain(for_type='Folder',
                                    to_workflow='plone_workflow')

        self.assertEquals(
            ['Anonymous'],
            self.get_allowed_roles_and_users(for_object=container))

    def assertReviewStates(self, expected):
        wftool = getToolByName(self.portal, 'portal_workflow')

        got = {}
        for obj in expected.keys():
            review_state = wftool.getInfoFor(obj, 'review_state')
            got[obj] = review_state

        self.assertEquals(
            expected, got, 'Unexpected workflow states')

    def set_workflow_chain(self, for_type, to_workflow):
        wftool = getToolByName(self.portal, 'portal_workflow')
        wftool.setChainForPortalTypes((for_type,),
                                      (to_workflow,))

    def assertSecurityIsUpToDate(self):
        wftool = getToolByName(self.portal, 'portal_workflow')
        updated_objects = wftool.updateRoleMappings()
        self.assertEquals(
            0, updated_objects,
            'Expected all objects to have an up to date security, but'
            ' there were some which were not up to date.')

    def get_allowed_roles_and_users(self, for_object):
        catalog = getToolByName(self.portal, 'portal_catalog')
        path = '/'.join(for_object.getPhysicalPath())
        rid = catalog.getrid(path)
        index_data = catalog.getIndexDataForRID(rid)
        return index_data.get('allowedRolesAndUsers')
