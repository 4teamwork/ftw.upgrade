from ftw.testbrowser import browsing
from ftw.upgrade.tests.base import JsonApiTestCase


class TestZopeAppJsonApi(JsonApiTestCase):

    def setUp(self):
        self.app = self.layer['app']

    @browsing
    def test_list_plone_sites(self, browser):
        self.api_request('GET', 'list_plone_sites', context=self.app)

        self.assert_json_equal(
            [{'id': 'plone',
              'path': '/plone',
              'title': 'Plone site'}],
            browser.json)
