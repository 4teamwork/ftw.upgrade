from AccessControl import getSecurityManager
from ftw.upgrade.jsonapi.base import APIView
from ftw.upgrade.jsonapi.utils import action
from ftw.upgrade.jsonapi.utils import jsonify


class ZopeAppAPI(APIView):

    @jsonify
    @action('GET')
    def list_plone_sites(self):
        """Returns a list of Plone sites.
        """

        return list(self._get_plone_sites())

    @jsonify
    @action('GET')
    def current_user(self):
        """Return the current user when authenticated properly.
        This can be used for testing authentication.
        """
        return getSecurityManager().getUser().getId()

    def _get_plone_sites(self):
        overview_view = self.context.restrictedTraverse('plone-overview')
        for site in overview_view.sites():
            yield {'id': site.getId(),
                   'path': '/'.join(site.getPhysicalPath()),
                   'title': site.Title()}
