from ftw.builder import Builder
from ftw.builder import create
from ftw.upgrade.placefulworkflow import PlacefulWorkflowPolicyActivator
from ftw.upgrade.testing import FTW_UPGRADE_FUNCTIONAL_TESTING
from ftw.upgrade.tests.base import WorkflowTestCase
from plone.app.testing import TEST_USER_ID
from plone.app.testing import TEST_USER_NAME
from plone.app.testing import login
from plone.app.testing import setRoles


class TestPlacefulWorkflowPolicyActivator(WorkflowTestCase):

    layer = FTW_UPGRADE_FUNCTIONAL_TESTING

    def setUp(self):
        super(TestPlacefulWorkflowPolicyActivator, self).setUp()
        self.portal = self.layer['portal']
        setRoles(self.portal, TEST_USER_ID, ['Manager'])
        login(self.portal, TEST_USER_NAME)

        self.set_workflow_chain(for_type='Folder',
                                to_workflow='intranet_workflow')
        self.set_workflow_chain(for_type='Document',
                                to_workflow='intranet_workflow')

    def test_activate_placeful_workflow_policy_with_mapping(self):
        container = create(Builder('folder')
                           .titled('Container')
                           .in_state('external'))

        subfolder = create(Builder('folder')
                           .within(container)
                           .titled('Subfolder')
                           .in_state('pending'))

        document = create(Builder('document')
                          .within(subfolder)
                          .titled('The Document')
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
                           .titled('Container')
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
                           .titled('Container')
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

        self.assertEquals(
            ['Anonymous'],
            self.get_allowed_roles_and_users(for_object=container))
