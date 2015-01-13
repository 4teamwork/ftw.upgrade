from ftw.testbrowser import browsing
from ftw.upgrade.tests.base import JsonApiTestCase


class TestZopeAppJsonApi(JsonApiTestCase):

    def setUp(self):
        self.app = self.layer['app']

    @browsing
    def test_api_discovery(self, browser):
        self.api_request('GET', '', context=self.app)

        self.assert_json_equal(
            {'actions':
                 [{'name': 'list_plone_sites',
                   'required_params': [],
                   'description': 'Returns a list of Plone sites.',
                   'request_method': 'GET'}]},

            browser.json)

    @browsing
    def test_list_plone_sites(self, browser):
        self.api_request('GET', 'list_plone_sites', context=self.app)

        self.assert_json_equal(
            [{'id': 'plone',
              'path': '/plone',
              'title': 'Plone site'}],
            browser.json)
