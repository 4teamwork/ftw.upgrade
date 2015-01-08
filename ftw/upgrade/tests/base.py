from contextlib import contextmanager
from ftw.builder import Builder
from ftw.builder import create
from ftw.upgrade.interfaces import IExecutioner
from ftw.upgrade.interfaces import IUpgradeInformationGatherer
from ftw.upgrade.testing import COMMAND_LAYER
from ftw.upgrade.testing import UPGRADE_FUNCTIONAL_TESTING
from operator import itemgetter
from path import Path
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from Products.CMFCore.utils import getToolByName
from unittest2 import TestCase
from zope.component import queryAdapter


class UpgradeTestCase(TestCase):
    layer = UPGRADE_FUNCTIONAL_TESTING

    def setUp(self):
        self.package = (Builder('python package')
                        .at_path(self.layer['temp_directory'])
                        .named('the.package'))
        self.portal = self.layer['portal']
        self.portal_setup = getToolByName(self.portal, 'portal_setup')
        self.portal_quickinstaller = getToolByName(self.portal, 'portal_quickinstaller')

    @contextmanager
    def package_created(self):
        with create(self.package).zcml_loaded(self.layer['configurationContext']) as package:
            yield package

    def default_upgrade(self):
        return Builder('plone upgrade step').upgrading('1000', to='1001')

    def install_profile(self, profileid, version=None):
        self.portal_setup.runAllImportStepsFromProfile('profile-{0}'.format(profileid))
        if version is not None:
            self.portal_setup.setLastVersionForProfile(profileid, (unicode(version),))

    def install_profile_upgrades(self, *profileids):
        gatherer = queryAdapter(self.portal_setup, IUpgradeInformationGatherer)
        upgrade_info = [(profile['id'], map(itemgetter('id'), profile['upgrades']))
                        for profile in gatherer.get_upgrades()
                        if profile['id'] in profileids]
        executioner = queryAdapter(self.portal_setup, IExecutioner)
        executioner.install(upgrade_info)

    def asset(self, filename):
        return Path(__file__).dirname().joinpath('assets', filename).text()


class CommandTestCase(TestCase):
    layer = COMMAND_LAYER

    def upgrade_script(self, args, assert_exitcode=True):
        command = ' '.join(('upgrade', args))
        return self.layer['execute_script'](command, assert_exitcode=assert_exitcode)


class WorkflowTestCase(TestCase):

    layer = UPGRADE_FUNCTIONAL_TESTING

    def setUp(self):
        self.portal = self.layer['portal']
        setRoles(self.portal, TEST_USER_ID, ['Manager'])

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

    def create_placeful_workflow_policy(self, named, with_workflows):
        placeful_wf_tool = getToolByName(
            self.portal, 'portal_placeful_workflow')

        placeful_wf_tool.manage_addWorkflowPolicy(named)
        policy = placeful_wf_tool.get(named)

        for portal_type, workflow in with_workflows.items():
            policy.setChain(portal_type, workflow)

        return policy

    def assert_permission_acquired(self, permission, obj, msg=None):
        not_acquired_permissions = self.get_not_acquired_permissions_of(obj)

        self.assertNotIn(
            permission, not_acquired_permissions,
            'Expected permission "%s" to be acquired on %s%s' % (
                permission, str(obj),
                msg and (' (%s)' % msg) or ''))

    def assert_permission_not_acquired(self, permission, obj, msg=None):
        not_acquired_permissions = self.get_not_acquired_permissions_of(obj)

        self.assertIn(
            permission, not_acquired_permissions,
            'Expected permission "%s" to NOT be acquired on %s%s' % (
                permission, str(obj),
                msg and (' (%s)' % msg) or ''))

    def get_not_acquired_permissions_of(self, obj):
        acquired_permissions = filter(
            lambda item: not item.get('acquire'),
            obj.permission_settings())

        return map(lambda item: item.get('name'), acquired_permissions)
