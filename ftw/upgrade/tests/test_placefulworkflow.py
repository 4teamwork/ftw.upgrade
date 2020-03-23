from ftw.builder import Builder
from ftw.builder import create
from ftw.upgrade.placefulworkflow import PlacefulWorkflowPolicyActivator
from ftw.upgrade.tests.base import WorkflowTestCase


class TestPlacefulWorkflowPolicyActivator(WorkflowTestCase):

    def setUp(self):
        super(TestPlacefulWorkflowPolicyActivator, self).setUp()

        self.set_workflow_chain(for_type='Folder',
                                to_workflow='intranet_workflow')
        self.set_workflow_chain(for_type='Document',
                                to_workflow='intranet_workflow')

    def test_activate_placeful_workflow_policy_with_mapping(self):
        container = create(Builder('folder')
                           .titled(u'Container')
                           .in_state('external'))

        subfolder = create(Builder('folder')
                           .within(container)
                           .titled(u'Subfolder')
                           .in_state('pending'))

        document = create(Builder('document')
                          .within(subfolder)
                          .titled(u'The Document')
                          .in_state('internally_published'))

        self.create_placeful_workflow_policy(
            named='local_workflow',
            with_workflows={
                'Folder': 'plone_workflow'})

        activator = PlacefulWorkflowPolicyActivator(container)
        activator.activate_policy(
            'local_workflow',
            review_state_mapping={
                ('intranet_workflow', 'plone_workflow'): {
                    'external': 'published',
                    'pending': 'pending'}})

        self.assertReviewStates({
                container: 'published',
                subfolder: 'pending',
                document: 'internally_published'})

    def test_object_security_is_updated(self):
        container = create(Builder('folder')
                           .titled(u'Container')
                           .in_state('external'))

        self.create_placeful_workflow_policy(
            named='local_workflow',
            with_workflows={
                'Folder': 'plone_workflow'})

        activator = PlacefulWorkflowPolicyActivator(container)
        activator.activate_policy(
            'local_workflow',
            review_state_mapping={
                ('intranet_workflow', 'plone_workflow'): {
                    'external': 'published'}})

        self.assertSecurityIsUpToDate()

    def test_object_security_is_reindexed(self):
        container = create(Builder('folder')
                           .titled(u'Container')
                           .in_state('internal'))

        self.assertIn('Member',
                      self.get_allowed_roles_and_users(for_object=container))

        self.create_placeful_workflow_policy(
            named='local_workflow',
            with_workflows={
                'Folder': 'plone_workflow'})

        activator = PlacefulWorkflowPolicyActivator(container)
        activator.activate_policy(
            'local_workflow',
            review_state_mapping={
                ('intranet_workflow', 'plone_workflow'): {
                    'internal': 'published'}})

        self.assertEqual(
            ['Anonymous'],
            self.get_allowed_roles_and_users(for_object=container))
