# pylint: disable=E0211, E0213
# E0211: Method has no argument
# E0213: Method should have "self" as first argument


from zope.interface import Interface, Attribute


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

    def __init__(portal_setup):
        """Adapts portal_setup.
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


class IExecutioner(Interface):
    """Executes multiple upgrade steps of multiple packages.
    Adapts the generic setup tool (portal_setup).
    """

    def __init__(portal_setup):
        """Adapts portal_setup.
        """

    def install(data):
        """Installs the dict data.
        data example:
        >>> {u'Products.CMFEditions:CMFEditions': '8159946379289711266'}
        """


class IUpgradeStep(Interface):
    """An upgrade step class providing tools and helpers for writing
    upgrade steps.

    Register the classmethod ``upgrade`` in ZCML.
    """

    portal_setup = Attribute('The portal_setup tool.')

    def __call__():
        """This method is implemented in each upgrade step with the
        tasks the upgrade should perform.
        """

    def getToolByName(tool_name):
        """Returns the tool with the name ``tool_name`` of the upgraded
        site.
        """

    def catalog_rebuild_index(name):
        """Reindex the ``portal_catalog`` index identified by ``name``.
        """

    def catalog_has_index(name):
        """Returns whether there is a catalog index ``name``.
        """

    def catalog_add_index(name, type_, extra=None):
        """Adds a new index to the ``portal_catalog`` tool.
        """

    def catalog_remove_index(name):
        """Removes an index to from ``portal_catalog`` tool.
        """

    def actions_remove_action(category, action_id):
        """Removes an action identified by ``action_id`` from
        the ``portal_actions`` tool from a particulary ``category``.
        """

    def actions_remove_type_action(portal_type, action_id):
        """Removes a ``portal_types`` action from the type identified
        by ``portal_type`` with the action id ``action_id``.
        """

    def set_property(context, key, value, data_type='string'):
        """Set a property with the key ``value`` and the value ``value``
        on the ``context`` safely. The property is created with the
        type ``data_type`` if it does not exist.
        """

    def add_lines_to_property(context, key, lines):
        """Updates a property with key ``key`` on the object ``context``
        adding ``lines``. The property is expected to by of type "lines".
        If the property does not exist it is created.
        """

    def setup_install_profile(profileid, steps=None):
        """Installs the generic setup profile identified by ``profileid``.
        If a list step names is passed with ``steps`` (e.g. ['actions']),
        only those steps are installed. All steps are installed by default.
        """
