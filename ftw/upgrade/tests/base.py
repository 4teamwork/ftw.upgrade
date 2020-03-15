from AccessControl import getSecurityManager
from AccessControl.SecurityManagement import setSecurityManager
from contextlib import contextmanager
from DateTime import DateTime
from ftw.builder import Builder
from ftw.builder import create
from ftw.testbrowser import browser
from ftw.upgrade.directory import scaffold
from ftw.upgrade.indexing import processQueue
from ftw.upgrade.interfaces import IExecutioner
from ftw.upgrade.interfaces import IUpgradeInformationGatherer
from ftw.upgrade.interfaces import IUpgradeStepRecorder
from ftw.upgrade.testing import COMMAND_AND_UPGRADE_FUNCTIONAL_TESTING
from ftw.upgrade.testing import COMMAND_LAYER
from ftw.upgrade.testing import UPGRADE_FUNCTIONAL_TESTING
from ftw.upgrade.tests.helpers import verbose_logging
from operator import itemgetter
from path import Path
from plone.app.testing import login
from plone.app.testing import setRoles
from plone.app.testing import SITE_OWNER_NAME
from plone.app.testing import TEST_USER_ID
from plone.app.testing import TEST_USER_PASSWORD
from Products.CMFCore.utils import getToolByName
from six import StringIO
from six.moves import map
from six.moves import zip
from unittest import TestCase
from zope.component import getMultiAdapter
from zope.component import queryAdapter

import json
import logging
import lxml.html
import os
import re
import six
import six.moves.urllib.error
import six.moves.urllib.parse
import six.moves.urllib.request
import transaction


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

    def login(self, user, browser=None):
        if hasattr(user, 'getUserName'):
            userid = user.getUserName()
        else:
            userid = user

        security_manager = getSecurityManager()
        if userid == SITE_OWNER_NAME:
            login(self.layer['app'], userid)
        else:
            login(self.portal, userid)

        if browser is not None:
            browser_auth_headers = [
                item for item in browser.session_headers
                if item[0] == 'Authorization'
            ]
            browser.login(userid)

        transaction.commit()

        @contextmanager
        def login_context_manager():
            try:
                yield
            finally:
                setSecurityManager(security_manager)
                if browser is not None:
                    browser.clear_request_header('Authorization')
                    [browser.append_request_header(name, value)
                     for (name, value) in browser_auth_headers]
                transaction.commit()

        return login_context_manager()

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
            self.portal_setup.setLastVersionForProfile(
                profileid, (six.text_type(version),))
        transaction.commit()

    def install_profile_upgrades(self, *profileids):
        gatherer = queryAdapter(self.portal_setup, IUpgradeInformationGatherer)
        upgrade_info = [
            (profile['id'], list(map(itemgetter('id'), profile['upgrades'])))
            for profile in gatherer.get_upgrades()
            if profile['id'] in profileids
        ]
        executioner = queryAdapter(self.portal_setup, IExecutioner)
        executioner.install(upgrade_info)

    def record_installed_upgrades(self, profile, *destinations):
        profile = re.sub('^profile-', '', profile)
        recorder = getMultiAdapter((self.portal, profile), IUpgradeStepRecorder)
        recorder.clear()
        list(map(recorder.mark_as_installed, destinations))
        transaction.commit()

    def clear_recorded_upgrades(self, profile):
        profile = re.sub('^profile-', '', profile)
        recorder = getMultiAdapter((self.portal, profile), IUpgradeStepRecorder)
        recorder.clear()
        transaction.commit()

    def assert_gathered_upgrades(self, expected, *args, **kwargs):
        gatherer = queryAdapter(self.portal_setup, IUpgradeInformationGatherer)
        result = gatherer.get_profiles(*args, **kwargs)
        got = {}
        for profile in result:
            if profile['id'] not in expected:
                continue

            got_profile = dict((key, []) for key in expected[profile['id']].keys())
            got[profile['id']] = got_profile

            for upgrade in profile['upgrades']:
                for key in got_profile.keys():
                    if upgrade[key]:
                        got_profile[key].append(upgrade['sdest'])

        self.maxDiff = None
        self.assertDictEqual(
            expected, got,
            'Unexpected gatherer result.\n\nPackages in result {0}:'.format(
                [profile['id'] for profile in result]))

    def asset(self, filename):
        return Path(__file__).dirname().joinpath('assets', filename).text()

    @contextmanager
    def assert_resources_recooked(self):
        def get_resources():
            doc = lxml.html.fromstring(self.portal())
            return list(map(str.strip, map(six.ensure_str, map(lxml.html.tostring,
                            doc.xpath('//link[@rel="stylesheet"][@href]'
                                      ' | //script[@src]')))))

        resources = get_resources()
        yield
        self.assertNotEqual(resources, get_resources(),
                            'Resurces are not recooked.')

    @contextmanager
    def assert_bundles_combined(self):
        # Note: this is for Plone 5.

        def get_timestamp():
            timestamp_file = self.portal.portal_resources.resource_overrides.production['timestamp.txt']
            # The data contains text, which should be a DateTime.
            # Convert it to an actual DateTime object so we can be sure when comparing it.
            return DateTime(timestamp_file.data.decode('utf8'))

        timestamp = get_timestamp()
        yield
        self.assertLess(timestamp, get_timestamp(),
                        'Timestamp has not been updated.')

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

        self.assertEqual(
            expected, got, 'Unexpected workflow states')

    def set_workflow_chain(self, for_type, to_workflow):
        wftool = getToolByName(self.portal, 'portal_workflow')
        wftool.setChainForPortalTypes((for_type,),
                                      (to_workflow,))

    def assertSecurityIsUpToDate(self):
        wftool = getToolByName(self.portal, 'portal_workflow')
        updated_objects = wftool.updateRoleMappings()
        self.assertEqual(
            0, updated_objects,
            'Expected all objects to have an up to date security, but'
            ' there were some which were not up to date.')

    def get_allowed_roles_and_users(self, for_object):
        processQueue()  # trigger async indexing
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
        acquired_permissions = [
            item for item in obj.permission_settings() if not item.get('acquire')]

        return [item.get('name') for item in acquired_permissions]


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
                    action, six.moves.urllib.parse.urlencode(data)))

            elif method.lower() == 'post':
                if not data:
                    data = {'enforce': 'post'}
                browser.visit(context, view='upgrades-api/{0}'.format(action),
                              data=data)

            else:
                raise Exception('Unsupported request method {0}'.format(method))

    @contextmanager
    def expect_api_error(self, status=None, message=None, details=None):
        api_error_info = {}
        with browser.expect_http_error(code=status):
            yield api_error_info

        expected = {'result': 'ERROR'}
        if message is not None:
            expected['message'] = message
        if details is not None:
            expected['details'] = details

        got = dict(zip(['result', 'message', 'details'], browser.json))

        self.assertDictContainsSubset(
            expected,
            got,
            'Unexpected error response details.\n\n'
            'Expected:' +
            json.dumps(expected, sort_keys=True, indent=4) +
            '\nto be included in:\n' +
            json.dumps(got, sort_keys=True, indent=4))


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
        # Determine the port the ZServer layer has picked
        test_instance_port = self.layer['port']
        self.write_zconf('instance', test_instance_port)
