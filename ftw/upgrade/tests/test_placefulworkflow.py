from Products.CMFCore.utils import getToolByName
from ftw.builder import Builder
from ftw.builder import create
from ftw.upgrade.placefulworkflow import PlacefulWorkflowPolicyActivator
from ftw.upgrade.testing import FTW_UPGRADE_FUNCTIONAL_TESTING
from plone.app.testing import TEST_USER_ID
from plone.app.testing import TEST_USER_NAME
from plone.app.testing import login
from plone.app.testing import setRoles
from unittest2 import TestCase


class TestPlacefulWorkflowPolicyActivator(TestCase):

    layer = FTW_UPGRADE_FUNCTIONAL_TESTING

    def setUp(self):
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

    def set_workflow_chain(self, for_type, to_workflow):
        wftool = getToolByName(self.portal, 'portal_workflow')
        wftool.setChainForPortalTypes((for_type,),
                                      (to_workflow,))

    def create_placeful_workflow_policy(self, named, with_workflows):
        placeful_wf_tool = getToolByName(
            self.portal, 'portal_placeful_workflow')

        placeful_wf_tool.manage_addWorkflowPolicy(named)
        policy = placeful_wf_tool.get(named)

        for portal_type, workflow in with_workflows.items():
            policy.setChain(portal_type, workflow)

        return policy

    def assertReviewStates(self, expected):
        wftool = getToolByName(self.portal, 'portal_workflow')

        got = {}
        for obj in expected.keys():
            review_state = wftool.getInfoFor(obj, 'review_state')
            got[obj] = review_state

        self.assertEquals(
            expected, got, 'Unexpected workflow states')

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
