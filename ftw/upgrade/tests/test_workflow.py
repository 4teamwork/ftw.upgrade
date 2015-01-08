from ftw.builder import Builder
from ftw.builder import create
from ftw.upgrade.placefulworkflow import PlacefulWorkflowPolicyActivator
from ftw.upgrade.tests.base import WorkflowTestCase
from ftw.upgrade.workflow import WorkflowChainUpdater
from ftw.upgrade.workflow import WorkflowSecurityUpdater
from Products.CMFCore.utils import getToolByName


class TestWorkflowChainUpdater(WorkflowTestCase):

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
                                    to_workflow='folder_workflow')

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

    def test_workflow_history_is_migrated(self):
        self.set_workflow_chain(for_type='Folder',
                                to_workflow='simple_publication_workflow')

        folder = create(Builder('folder'))
        self.execute_transition(folder, 'publish')

        self.assert_workflow_history_length(folder, 2)
        self.assert_workflow_history_entry(folder, {
                'action': 'publish',
                'actor': 'test_user_1_',
                'comments': '',
                'review_state': 'published'})

        mapping = {
            ('simple_publication_workflow', 'folder_workflow'): {
                'published': 'published'}}
        with WorkflowChainUpdater([folder], mapping):
            self.set_workflow_chain(for_type='Folder',
                                    to_workflow='folder_workflow')

        self.assert_workflow_history_length(folder, 3)
        self.assert_workflow_history_entry(folder, {
                'action': 'publish',
                'actor': 'test_user_1_',
                'comments': '',
                'review_state': 'published'}, -2)

    def test_workflow_history_is_not_migrated_when_migration_disabled(self):
        self.set_workflow_chain(for_type='Folder',
                                to_workflow='simple_publication_workflow')

        folder = create(Builder('folder'))
        self.assert_workflow_history_length(folder, 1)

        mapping = {
            ('simple_publication_workflow', 'folder_workflow'): {
                'published': 'published'}}
        with WorkflowChainUpdater([folder], mapping,
                                  migrate_workflow_history=False):
            self.set_workflow_chain(for_type='Folder',
                                    to_workflow='folder_workflow')

        self.assert_workflow_history_length(folder, 0)

    def test_workflow_history_transition_is_updated_when_mapped(self):
        self.set_workflow_chain(for_type='Folder',
                                to_workflow='simple_publication_workflow')

        folder = create(Builder('folder'))
        self.execute_transition(folder, 'publish')

        self.assert_workflow_history_length(folder, 2)
        self.assert_workflow_history_entry(folder, {
                'action': 'publish',
                'actor': 'test_user_1_',
                'comments': '',
                'review_state': 'published'})

        mapping = {
            ('simple_publication_workflow', 'folder_workflow'): {
                'published': 'published'}}
        transition_mapping = {
            ('simple_publication_workflow', 'folder_workflow'): {
                'publish': 'publish'}}

        with WorkflowChainUpdater([folder], mapping,
                                  transition_mapping=transition_mapping):
            self.set_workflow_chain(for_type='Folder',
                                    to_workflow='folder_workflow')

        self.assert_workflow_history_length(folder, 3)
        self.assert_workflow_history_entry(folder, {
                'action': 'publish',
                'actor': 'test_user_1_',
                'comments': '',
                'review_state': 'published'}, -2)

    def execute_transition(self, context, transition):
        wftool = getToolByName(self.layer['portal'], 'portal_workflow')
        wftool.doActionFor(context, transition)

    def assert_workflow_history_entry(self, context, expected, index=-1):
        wftool = getToolByName(self.layer['portal'], 'portal_workflow')
        history = wftool.getInfoFor(context, 'review_history')
        self.assertDictContainsSubset(
            expected, history[index],
            'Workflow history entry is wrong.\n{0}'.format(history))

    def assert_workflow_history_length(self, context, length):
        wftool = getToolByName(self.layer['portal'], 'portal_workflow')
        history = wftool.getInfoFor(context, 'review_history')
        self.assertEquals(
            length, len(history),
            'Workflow history length is wrong.\n{0}'.format(history))


class TestWorkflowSecurityUpdater(WorkflowTestCase):

    def test_updates_only_objects_with_specified_workflows(self):
        self.set_workflow_chain(for_type='Folder',
                                to_workflow='folder_workflow')
        folder = create(Builder('folder'))
        folder.manage_permission('View', roles=[],
                                 acquire=True)

        self.set_workflow_chain(for_type='Document',
                                to_workflow='simple_publication_workflow')
        document = create(Builder('document'))
        document.manage_permission('View', roles=[],
                                   acquire=True)

        self.assert_permission_acquired('View', folder)
        self.assert_permission_acquired('View', document)

        updater = WorkflowSecurityUpdater()
        updater.update(['folder_workflow'])

        self.assert_permission_not_acquired(
            'View', folder, 'The folder should have been updated but wasnt.')
        self.assert_permission_acquired(
            'View', document,
            'The document should NOT have been updated but it was.')

    def test_updates_disabling_update_security(self):
        self.set_workflow_chain(for_type='Folder',
                                to_workflow='folder_workflow')
        folder = create(Builder('folder'))
        folder.manage_permission('View', roles=['Reader'], acquire=False)
        folder.reindexObjectSecurity()
        self.assertEquals(['Reader'],
                          self.get_allowed_roles_and_users(for_object=folder))

        updater = WorkflowSecurityUpdater()
        updater.update(['folder_workflow'], reindex_security=False)
        self.assertEquals(['Reader'],
                          self.get_allowed_roles_and_users(for_object=folder))

        updater.update(['folder_workflow'], reindex_security=True)
        self.assertEquals(['Anonymous'],
                          self.get_allowed_roles_and_users(for_object=folder))

    def test_respects_placeful_workflows_when_updating(self):
        container = create(Builder('folder'))
        document = create(Builder('document').within(container))

        self.create_placeful_workflow_policy(
            named='local_workflow',
            with_workflows={'Document': 'simple_publication_workflow'})
        activator = PlacefulWorkflowPolicyActivator(container)
        activator.activate_policy(
            'local_workflow',
            review_state_mapping={
                (None, 'simple_publication_workflow'): {
                    None: 'private'}})

        document.manage_permission('View', roles=[],
                                   acquire=True)
        self.assert_permission_acquired('View', document)

        updater = WorkflowSecurityUpdater()
        updater.update(['simple_publication_workflow'])

        self.assert_permission_not_acquired(
            'View', document,
            'The document should have been updated but was not.')
