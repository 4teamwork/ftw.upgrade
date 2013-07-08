# pylint: disable=E0211, E0213
# E0211: Method has no argument
# E0213: Method should have "self" as first argument


from zope.interface import Interface


class IUpgradablePloneSite(Interface):
    """Interface describing an upgradable Plone site.

    Adapts a Plone site to be upgraded (or queried for upgrade related
    information).
    """

    def __init__(plone_site):
        """Adapts IPloneSiteRoot.
        """

    def is_upgradable():
        """True if the site has proposed upgrades, False otherwise.
        """

    def get_upgrades(proposed=True):
        """List upgrades for the adapted Plone site.

        If `proposed` is True (default), only proposed upgrades will be returned.
        Otherwise all the upgrades will be listed.
        """


class IUpgradableZopeApp(Interface):
    """Interface describing a Zope Application with upgradable Plone sites.

    Adapts a Zope Application Root containing one or more Plone sites to be
    upgraded.
    """


    def __init__(app):
        """Adapts IApplication.
        """

    def get_plone_sites(upgradable=False):
        """List all Plone sites.

        If `upgradable` is True, only lists sites that have proposed upgrades.
        """

