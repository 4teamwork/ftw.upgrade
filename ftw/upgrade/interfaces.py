# pylint: disable=E0211, E0213
# E0211: Method has no argument
# E0213: Method should have "self" as first argument


from zope.interface import Interface


class IUpgradeLayer(Interface):
    """ftw.upgrade specific browser layer.
    """


class IUpgradeInformationGatherer(Interface):
    """An adapter adpting the generic setup tool (portal_setup), providing
    a cleaned up list of upgrades grouped by profile.

    - Upgrade groups are flattened for simplicity.
    - Only profiles installed on this plone site are listed.
    - Products.CMFPlone is not listed. I thas its own migration mechanism.
    - Upgrades are grouped by done / proposed.
    """

    def get_upgrades():
        """Returns upgrades grouped by done / proposed and assigned profile.

        Example output:
        >>> [{'db_version': u'3',
        ...   'product': 'Products.CMFEditions',
        ...   'description': u'Extension profile for default ' + \
        ...       'CMFEditions setup.',
        ...   'for': None,
        ...   'title': u'CMFEditions',
        ...   'version': u'3',
        ...   'upgrades': [
        ...       {'haspath': ('3',
        ...                   ),
        ...        'description': None,
        ...        'proposed': False,
        ...        'title': u'Fix portal_historyidhandler',
        ...        'dest': ('3',
        ...                ),
        ...        'ssource': '2.0',
        ...        'sortkey': 0,
        ...        'source': ('2',
        ...                   '0'),
        ...        'step': <Products.GenericSetup.upgrade...>,
        ...        'done': True,
        ...        'id': '8159946379289711266',
        ...        'sdest': '3'}],
        ...   'path': u'/.../profiles/default',
        ...   'type': 2,
        ...   'id': u'Products.CMFEditions:CMFEditions'}]
        """
