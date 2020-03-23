from datetime import datetime
from ftw.builder import Builder
from ftw.testbrowser import browsing
from ftw.testbrowser.pages import statusmessages
from ftw.upgrade.browser.manage import ResponseLogger
from ftw.upgrade.tests.base import UpgradeTestCase
from plone.app.testing import SITE_OWNER_NAME
from Products.CMFCore.utils import getToolByName
from six import BytesIO
from unittest import TestCase

import logging
import re
import transaction


class TestResponseLogger(TestCase):

    def test_logging(self):
        response = BytesIO()

        with ResponseLogger(response):
            logging.error('foo')
            logging.error('bar')

        response.seek(0)
        self.assertEqual(
            [b'foo', b'bar'],
            response.read().strip().split(b'\n'))

    def test_logged_tags_get_escaped(self):
        response = BytesIO()

        with ResponseLogger(response):
            logging.error('ERROR: Something at <TextBlock at /bla/blub>')

        response.seek(0)
        self.assertEqual(
            [b'ERROR: Something at &lt;TextBlock at /bla/blub&gt;'],
            response.read().strip().split(b'\n'))

    def test_logging_exceptions(self):
        response = BytesIO()

        with self.assertRaises(KeyError):
            with ResponseLogger(response):
                raise KeyError('foo')

        response.seek(0)
        output = response.read().strip()
        # Dynamically replace paths so that it works on all machines
        output = re.sub(br'(File ").*(ftw/upgrade/.*")',
                        br'\1/.../\2', output)
        output = re.sub(br'(line )\d*', br'line XX', output)

        self.assertEqual(
            [b'FAILED',
             b'Traceback (most recent call last):',
             b'  File "/.../ftw/upgrade/tests/'
             b'test_manage_view.py", line XX, in test_logging_exceptions',
             b"    raise KeyError('foo')",
             b"KeyError: 'foo'"],
            output.split(b'\n'))

    def test_annotate_result_on_success(self):
        response = BytesIO()

        with ResponseLogger(response, annotate_result=True):
            logging.error('foo')
            logging.error('bar')

        response.seek(0)
        self.assertEqual(
            [b'foo', b'bar', b'Result: SUCCESS'],
            response.read().strip().split(b'\n'))

    def test_annotate_result_on_error(self):
        response = BytesIO()

        with self.assertRaises(KeyError):
            with ResponseLogger(response, annotate_result=True):
                raise KeyError('foo')

        response.seek(0)
        output = response.read().strip()
        # Dynamically replace paths so that it works on all machines
        output = re.sub(br'(File ").*(ftw/upgrade/.*")',
                        br'\1/.../\2', output)
        output = re.sub(br'(line )\d*', br'line XX', output)

        self.assertEqual(
            [b'FAILED',
             b'Traceback (most recent call last):',
             b'  File "/.../ftw/upgrade/tests/'
             b'test_manage_view.py", line XX, in test_annotate_result_on_error',
             b"    raise KeyError('foo')",
             b"KeyError: 'foo'",
             b'Result: FAILURE'],
            output.split(b'\n'))


class TestManageUpgrades(UpgradeTestCase):

    def setUp(self):
        super(TestManageUpgrades, self).setUp()
        self.portal_url = self.layer['portal'].portal_url()
        self.portal = self.layer['portal']

    def assertEqualURL(self, first, second, msg=None):
        # WebOb generates requests that always contain the port even for the
        # default port 80.
        return self.assertEqual(
            first.replace(':80', ''), second.replace(':80', ''), msg)

    @browsing
    def test_registered_in_controlpanel(self, browser):
        browser.login(SITE_OWNER_NAME).open(view='overview-controlpanel')
        link = browser.css('#content').find('Upgrades').first
        self.assertEqualURL(self.portal_url + '/@@manage-upgrades', link.attrib['href'])

    @browsing
    def test_manage_view_renders(self, browser):
        browser.login(SITE_OWNER_NAME).open(view='manage-upgrades')

        up_link = browser.css('#content').find('Up to Site Setup').first
        self.assertEqualURL(self.portal_url + '/@@overview-controlpanel',
                            up_link.attrib['href'])

        self.assertTrue(browser.css('input[value="plone.app.discussion:default"]').first)

    @browsing
    def test_manage_plain_view_renders(self, browser):
        browser.login(SITE_OWNER_NAME).open(view='manage-upgrades-plain')
        self.assertTrue(browser.css('input[value="plone.app.discussion:default"]').first)

    @browsing
    def test_manage_view_pre_selects_deferrable_upgrades(self, browser):
        self.package.with_profile(
            Builder('genericsetup profile')
            .with_upgrade(Builder('ftw upgrade step')
                          .to(datetime(2011, 1, 1))
                          .as_deferrable()))

        with self.package_created():
            self.install_profile('the.package:default', version='1')
            self.clear_recorded_upgrades('the.package:default')
            transaction.commit()

            transaction.begin()  # sync transaction
            browser.login(SITE_OWNER_NAME).open(view='manage-upgrades')
            deferrable_upgrade_checkbox = browser.css(
                'input[id|="the.package:default"]').first
            self.assertTrue(deferrable_upgrade_checkbox.checked)

    @browsing
    def test_install(self, browser):
        def upgrade_step(setup_context):
            portal = getToolByName(setup_context, 'portal_url').getPortalObject()
            portal.upgrade_installed = True

        self.package.with_profile(Builder('genericsetup profile')
                                  .with_upgrade(Builder('plone upgrade step')
                                                .upgrading('1111', '2222')
                                                .calling(upgrade_step, getToolByName)))

        with self.package_created():
            self.install_profile('the.package:default', '1111')
            self.portal.upgrade_installed = False
            transaction.commit()

            transaction.begin()  # sync transaction
            self.assertFalse(self.portal.upgrade_installed)

            browser.login(SITE_OWNER_NAME).open(view='manage-upgrades')
            # Install proposed upgrades
            browser.find('Install').click()

            transaction.begin()  # sync transaction
            self.assertTrue(self.portal.upgrade_installed)

    @browsing
    def test_upgrades_view_shows_cyclic_dependencies_error(self, browser):
        self.package.with_profile(Builder('genericsetup profile')
                                  .named('foo')
                                  .with_dependencies('the.package:bar'))
        self.package.with_profile(Builder('genericsetup profile')
                                  .named('bar')
                                  .with_dependencies('the.package:foo'))

        with self.package_created():
            self.install_profile('the.package:foo')
            self.install_profile('the.package:bar')
            transaction.commit()

            browser.login(SITE_OWNER_NAME).open(view='@@manage-upgrades')
            statusmessages.assert_message('There are cyclic dependencies.'
                                          ' The profiles could not be sorted'
                                          ' by dependencies!')

            possibilities = (
                ['the.package:foo ; the.package:bar'],
                ['the.package:bar ; the.package:foo'])

            self.assertIn(browser.css('.cyclic-dependencies li').text, possibilities)
