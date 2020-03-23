from ftw.testbrowser import browsing
from ftw.upgrade.tests.base import JsonApiTestCase


class TestZopeAppJsonApi(JsonApiTestCase):

    def setUp(self):
        self.app = self.layer['app']

    @browsing
    def test_api_discovery(self, browser):
        self.api_request('GET', '', context=self.app)

        self.assert_json_equal(
            {'api_version': 'v1',
             'actions':
                 [{'name': 'current_user',
                   'required_params': [],
                   'description': 'Return the current user when authenticated properly.'
                   ' This can be used for testing authentication.',
                   'request_method': 'GET'},

                  {'name': 'list_plone_sites',
                   'required_params': [],
                   'description': 'Returns a list of Plone sites.',
                   'request_method': 'GET'}]},

            browser.json)

        self.assertTrue(browser.body.endswith(b'\n'),
                        'There should always be a trailing newline.')

    @browsing
    def test_list_plone_sites(self, browser):
        self.api_request('GET', 'list_plone_sites', context=self.app)

        self.assert_json_equal(
            [{'id': 'plone',
              'path': '/plone',
              'title': 'Plone site'}],
            browser.json)

    @browsing
    def test_current_user(self, browser):
        self.api_request('GET', 'current_user', context=self.app)
        self.assertEqual('admin', browser.json)

    @browsing
    def test_requiring_available_api_version_by_url(self, browser):
        self.api_request('GET', 'v1/list_plone_sites', context=self.app)
        self.assert_json_equal(
            [{'id': 'plone',
              'path': '/plone',
              'title': 'Plone site'}],
            browser.json)

    @browsing
    def test_requiring_wrong_api_version_by_url(self, browser):
        with self.expect_api_error(status=404,
                                   message='Wrong API version',
                                   details='The API version "v100" is not available.'):
            self.api_request('GET', 'v100/list_plone_sites', context=self.app)

        self.assertTrue(browser.body.endswith(b'\n'),
                        'There should always be a trailing newline.')

    @browsing
    def test_requesting_unkown_action(self, browser):
        with self.expect_api_error(status=404,
                                   message='Unkown API action',
                                   details='There is no API action "something".'):
            self.api_request('GET', 'something', context=self.app)
