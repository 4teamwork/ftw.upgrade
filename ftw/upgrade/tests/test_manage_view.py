from ftw.upgrade.testing import FTW_UPGRADE_FUNCTIONAL_TESTING
from plone.app.testing import TEST_USER_NAME, TEST_USER_PASSWORD
from plone.testing.z2 import Browser
from unittest2 import TestCase


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
