from ftw.builder import Builder
from ftw.builder import create
from ftw.upgrade.testing import FTW_UPGRADE_INTEGRATION_TESTING
from ftw.upgrade.tests.base import WorkflowTestCase
from ftw.upgrade.workflow import WorkflowChainUpdater


class TestWorkflowChainUpdater(WorkflowTestCase):

    layer = FTW_UPGRADE_INTEGRATION_TESTING

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
