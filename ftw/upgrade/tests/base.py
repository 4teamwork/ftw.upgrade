from contextlib import contextmanager
from ftw.builder import Builder
from ftw.builder import create
from ftw.testbrowser import browser
from ftw.upgrade.directory import scaffold
from ftw.upgrade.interfaces import IExecutioner
from ftw.upgrade.interfaces import IUpgradeInformationGatherer
from ftw.upgrade.interfaces import IUpgradeStepRecorder
from ftw.upgrade.testing import COMMAND_AND_UPGRADE_FUNCTIONAL_TESTING
from ftw.upgrade.testing import COMMAND_LAYER
from ftw.upgrade.testing import UPGRADE_FUNCTIONAL_TESTING
from ftw.upgrade.tests.helpers import verbose_logging
from operator import itemgetter
from path import Path
from plone.app.testing import setRoles
from plone.app.testing import SITE_OWNER_NAME
from plone.app.testing import TEST_USER_ID
from plone.app.testing import TEST_USER_PASSWORD
from Products.CMFCore.utils import getToolByName
from StringIO import StringIO
from unittest2 import TestCase
from urllib2 import HTTPError
from zope.component import getMultiAdapter
from zope.component import queryAdapter
import json
import logging
import os
import re
import transaction
import urllib


class UpgradeTestCase(TestCase):
    layer = UPGRADE_FUNCTIONAL_TESTING

    def setUp(self):
        self.package = (Builder('python package')
                        .at_path(self.directory)
                        .named('the.package'))
        self.portal = self.layer['portal']
        self.portal_setup = getToolByName(self.portal, 'portal_setup')
        self.portal_quickinstaller = getToolByName(self.portal, 'portal_quickinstaller')

    def tearDown(self):
        self.teardown_logging()

    def grant(self, *roles):
        setRoles(self.portal, TEST_USER_ID, list(roles))
        transaction.commit()

    @property
    def directory(self):
        return self.layer['temp_directory']

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
        transaction.commit()

    def install_profile_upgrades(self, *profileids):
        gatherer = queryAdapter(self.portal_setup, IUpgradeInformationGatherer)
        upgrade_info = [(profile['id'], map(itemgetter('id'), profile['upgrades']))
                        for profile in gatherer.get_upgrades()
                        if profile['id'] in profileids]
        executioner = queryAdapter(self.portal_setup, IExecutioner)
        executioner.install(upgrade_info)

    def record_installed_upgrades(self, profile, *destinations):
        profile = re.sub('^profile-', '', profile)
        recorder = getMultiAdapter((self.portal, profile), IUpgradeStepRecorder)
        recorder.clear()
        map(recorder.mark_as_installed, destinations)
        transaction.commit()

    def clear_recorded_upgrades(self, profile):
        profile = re.sub('^profile-', '', profile)
        recorder = getMultiAdapter((self.portal, profile), IUpgradeStepRecorder)
        recorder.clear()
        transaction.commit()

    def asset(self, filename):
        return Path(__file__).dirname().joinpath('assets', filename).text()

    @contextmanager
    def assert_resources_recooked(self):
        def get_styles():
            return self.portal.restrictedTraverse(
                'resourceregistries_styles_view').styles()

        def get_scripts():
            return self.portal.restrictedTraverse(
                'resourceregistries_scripts_view').scripts()

        styles = get_styles()
        scripts = get_scripts()
        yield
        self.assertNotEqual(styles, get_styles(), 'Styles are not recooked.')
        self.assertNotEqual(scripts, get_scripts(), 'Scripts are not recooked.')

    def setup_logging(self):
        self.log = StringIO()
        self.loghandler = logging.StreamHandler(self.log)
        self.logger = logging.getLogger('ftw.upgrade')
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(self.loghandler)

    def teardown_logging(self):
        if getattr(self, 'log', None) is None:
            return

        self.logger.removeHandler(self.loghandler)
        self.log = None
        self.loghandler = None
        self.logger = None

    def get_log(self):
        return self.log.getvalue().splitlines()

    def purge_log(self):
        self.log.seek(0)
        self.log.truncate()


class CommandTestCase(TestCase):
    layer = COMMAND_LAYER

    def upgrade_script(self, args, assert_exitcode=True):
        command = ' '.join(('upgrade', args))
        exitcode, output = self.layer['execute_script'](
            command, assert_exitcode=assert_exitcode)

        output = (re.compile(r'/[^\n]*Terminal kind \'dumb\'[^\n]*\n', re.M)
                  .sub('', output))
        output = (re.compile(r'^[^\n]*_BINTERM_UNSUPPORTED[^\n]*\n', re.M)
                  .sub('', output))
        return exitcode, output


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


class JsonApiTestCase(UpgradeTestCase):

    def assert_json_equal(self, expected, got, msg=None):
        expected = json.dumps(expected, sort_keys=True, indent=4)
        got = json.dumps(got, sort_keys=True, indent=4)
        self.maxDiff = None
        self.assertMultiLineEqual(expected, got, msg)

    def assert_json_contains_profile(self, expected_profileinfo, got, msg=None):
        profileid = expected_profileinfo['id']
        got_profiles = dict([(profile['id'], profile) for profile in got])
        self.assertIn(profileid, got_profiles,
                      'assert_json_contains_profile: expected profile not in JSON')
        self.assert_json_equal(expected_profileinfo, got_profiles[profileid], msg)

    def assert_json_contains(self, expected_element, got_elements):
        message = 'Could not find:\n\n{0}\n\nin list:\n\n{0}'.format(
            json.dumps(expected_element, sort_keys=True, indent=4),
            json.dumps(got_elements, sort_keys=True, indent=4))
        self.assertTrue(expected_element in got_elements, message)

    def is_installed(self, profileid, dest_time):
        recorder = getMultiAdapter((self.portal, profileid), IUpgradeStepRecorder)
        return recorder.is_installed(dest_time.strftime(scaffold.DATETIME_FORMAT))

    def api_request(self, method, action, data=(), authenticate=True,
                    context=None):
        if context is None:
            context = self.layer['portal']
        if authenticate:
            browser.login(SITE_OWNER_NAME)
        else:
            browser.logout()

        with verbose_logging():
            if method.lower() == 'get':
                browser.visit(context, view='upgrades-api/{0}?{1}'.format(
                        action,
                        urllib.urlencode(data)))

            elif method.lower() == 'post':
                if not data:
                    data = {'enforce': 'post'}
                browser.visit(context, view='upgrades-api/{0}'.format(action),
                              data=data)

            else:
                raise Exception('Unsupported request method {0}'.format(method))

    @contextmanager
    def expect_api_error(self, **expectations):
        api_error_info = {}
        with self.expect_request_error() as response_info:
            yield api_error_info

        api_error_info.update(response_info)
        # del api_error_info['headers']  # not serializable
        api_error_info['response_message'] = response_info['message']

        # Make headers serializable
        api_error_info['headers'] = dict(api_error_info['headers'])

        try:
            body_json = json.loads(response_info['body'])
            assert len(body_json) == 3
            assert body_json[0] == 'ERROR'
            api_error_info['message'] = body_json[1]
            api_error_info['details'] = body_json[2]
        except:
            raise AssertionError(
                'Unexpected error response body. A three item list is expected,'
                ' consisting of "ERROR", the error message (short) and the error details.\n'
                'Response body: {0}'.format(response_info['body']))

        self.assertDictContainsSubset(
            expectations, api_error_info,
            'Unexpected error response details.\n\n'
            'Expected:' +
            json.dumps(expectations, sort_keys=True, indent=4) +
            '\nto be included in:\n' +
            json.dumps(api_error_info, sort_keys=True, indent=4))

    @contextmanager
    def expect_request_error(self):
        response_info = {}
        with self.assertRaises(HTTPError) as cm:
            yield response_info

        exc = cm.exception
        response_info['status'] = exc.wrapped.code
        response_info['message'] = exc.wrapped.msg
        response_info['url'] = exc.wrapped._url
        response_info['headers'] = exc.hdrs
        response_info['body'] = exc.wrapped.read()


class CommandAndInstanceTestCase(JsonApiTestCase, CommandTestCase):
    layer = COMMAND_AND_UPGRADE_FUNCTIONAL_TESTING

    def setUp(self):
        super(CommandAndInstanceTestCase, self).setUp()
        self.directory.joinpath('var').mkdir_p()
        os.environ['UPGRADE_AUTHENTICATION'] = ':'.join((SITE_OWNER_NAME,
                                                         TEST_USER_PASSWORD))

    def tearDown(self):
        if 'UPGRADE_AUTHENTICATION' in os.environ:
            del os.environ['UPGRADE_AUTHENTICATION']
        if 'UPGRADE_PUBLIC_URL' in os.environ:
            del os.environ['UPGRADE_PUBLIC_URL']

    @property
    def directory(self):
        return self.layer['root_path']

    def write_zconf(self, instance_name, port):
        etc1 = self.layer['root_path'].joinpath('parts', instance_name, 'etc')
        etc1.makedirs()
        etc1.joinpath('zope.conf').write_text(
            '\n'.join(('<http-server>',
                       '  address {0}'.format(port),
                       '</http-server>')))
        return etc1.dirname()

    def write_zconf_with_test_instance(self):
        test_instance_port = os.environ.get('ZSERVER_PORT', 55001)
        self.write_zconf('instance', test_instance_port)
