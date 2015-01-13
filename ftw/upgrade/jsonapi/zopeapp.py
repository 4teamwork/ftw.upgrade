from ftw.upgrade.jsonapi.utils import action
from ftw.upgrade.jsonapi.utils import jsonify
from zope.publisher.browser import BrowserView


class ZopeAppAPI(BrowserView):

    @jsonify
    @action('GET')
    def list_plone_sites(self):
        """Returns a list of plone sites.
        """

        return list(self._get_plone_sites())

    def _get_plone_sites(self):
        overview_view = self.context.restrictedTraverse('plone-overview')
        for site in overview_view.sites():
            yield {'id': site.getId(),
                   'path': '/'.join(site.getPhysicalPath()),
                   'title': site.Title()}
