from Products.CMFCore.utils import getToolByName
from StringIO import StringIO
from ftw.testbrowser import browsing
from ftw.testbrowser.pages import statusmessages
from ftw.upgrade.browser.manage import ResponseLogger
from ftw.upgrade.testing import CYCLIC_DEPENDENCIES_FUNCTIONAL
from ftw.upgrade.testing import FTW_UPGRADE_FUNCTIONAL_TESTING
from plone.app.testing import TEST_USER_NAME, TEST_USER_PASSWORD
from plone.testing.z2 import Browser
from unittest2 import TestCase
import logging
import re
import transaction


class TestResponseLogger(TestCase):

    def test_logging(self):
        response = StringIO()

        with ResponseLogger(response):
            logging.error('foo')
            logging.error('bar')

        response.seek(0)
        self.assertEqual(
            ['foo', u'bar'],
            response.read().strip().split('\n'))

    def test_logging_exceptions(self):
        response = StringIO()

        with self.assertRaises(KeyError):
            with ResponseLogger(response):
                raise KeyError('foo')

        response.seek(0)
        output = response.read().strip()
        # Dynamically replace paths so that it works on all machines
        output = re.sub(r'(File ").*(ftw/upgrade/.*")',
                        r'\1/.../\2', output)
        output = re.sub(r'(line )\d*', r'line XX', output)

        self.assertEqual(
            ['FAILED',
             'Traceback (most recent call last):',
             '  File "/.../ftw/upgrade/tests/'
             'test_manage_view.py", line XX, in test_logging_exceptions',
             "    raise KeyError('foo')",
             "KeyError: 'foo'"],
            output.split('\n'))


class TestManageUpgrades(TestCase):

    layer = FTW_UPGRADE_FUNCTIONAL_TESTING

    def setUp(self):
        super(TestManageUpgrades, self).setUp()

        self.portal_url = self.layer['portal'].portal_url()

        self.browser = Browser(self.layer['app'])
        self.browser.handleErrors = False
        self.browser.addHeader('Authorization', 'Basic %s:%s' % (
                TEST_USER_NAME, TEST_USER_PASSWORD,))

    def test_registered_in_controlpanel(self):
        self.browser.open(self.portal_url + '/@@overview-controlpanel')
        link = self.browser.getLink('Upgrades')
        self.assertEqual(self.portal_url + '/@@manage-upgrades', link.url)

    def test_manage_view_renders(self):
        self.browser.open(self.portal_url + '/@@manage-upgrades')

        link = self.browser.getLink('Up to Site Setup')
        self.assertEqual(self.portal_url + '/@@overview-controlpanel', link.url)

        self.assertIn('plone.app.discussion:default', self.browser.contents)

    def test_install(self):
        profileid = 'ftw.upgrade.tests.profiles:navigation-index'
        portal_setup = getToolByName(self.layer['portal'], 'portal_setup')
        portal_setup.runAllImportStepsFromProfile(
            'profile-%s' % profileid,
            purge_old=False)
        transaction.commit()

        catalog = getToolByName(self.layer['portal'], 'portal_catalog')
        self.assertEqual(
            'KeywordIndex',
            type(catalog.Indexes.get('excludeFromNav')).__name__)

        self.browser.open(self.portal_url + '/@@manage-upgrades')
        self.assertIn('ftw.upgrade.tests.profiles:navigation-index',
                      self.browser.contents)

        # This upgrade changes KeywordIndex -> FieldIndex

        self.browser.getControl(name='submitted').click()

        self.assertEqual(
            'FieldIndex',
            type(catalog.Indexes.get('excludeFromNav')).__name__)


class TestManageUpgradesCyclicDependencies(TestCase):
    """The layer of this test case loads GS profiles "first" and "second",
    which have cyclic dependencies.
    """

    layer = CYCLIC_DEPENDENCIES_FUNCTIONAL

    @browsing
    def test_upgrades_view_shows_cyclic_dependencies_error(self, browser):
        browser.login().open(view='@@manage-upgrades')
        statusmessages.assert_message('There are cyclic dependencies.'
                                      ' The profiles could not be sorted'
                                      ' by dependencies!')

        possibibilites = (
            ['ftw.upgrade.tests.profiles:first ; ftw.upgrade.tests.profiles:second'],
            ['ftw.upgrade.tests.profiles:second ; ftw.upgrade.tests.profiles:first'])

        self.assertIn(browser.css('.cyclic-dependencies li').text, possibibilites)
