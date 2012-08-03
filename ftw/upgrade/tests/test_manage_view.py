from Products.CMFCore.utils import getToolByName
from StringIO import StringIO
from ftw.upgrade.browser.manage import ResponseLogger
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
        self.assertEqual(response.read().strip().split('\n'),
                         ['foo', u'bar'])

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

        self.assertEqual(
            output.split('\n'),

            ['FAILED',
             'Traceback (most recent call last):',
             '  File "/.../ftw/upgrade/tests/'
             'test_manage_view.py", line 31, in test_logging_exceptions',
             "    raise KeyError('foo')",
             "KeyError: 'foo'"])


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
        self.assertEqual(link.url, self.portal_url + '/@@manage-upgrades')

    def test_manage_view_renders(self):
        self.browser.open(self.portal_url + '/@@manage-upgrades')

        link = self.browser.getLink('Up to Site Setup')
        self.assertEqual(link.url,
                         self.portal_url + '/@@overview-controlpanel')

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
            type(catalog.Indexes.get('excludeFromNav')).__name__,
            'KeywordIndex')

        self.browser.open(self.portal_url + '/@@manage-upgrades')
        self.assertIn('ftw.upgrade.tests.profiles:navigation-index',
                      self.browser.contents)

        # This upgrade changes KeywordIndex -> FieldIndex

        self.browser.getControl(name='submitted').click()

        self.assertEqual(
            type(catalog.Indexes.get('excludeFromNav')).__name__,
            'FieldIndex')
