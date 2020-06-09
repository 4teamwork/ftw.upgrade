# pylint: disable=E0211, E0213
# E0211: Method has no argument
# E0213: Method should have "self" as first argument


from zope.interface import Attribute
from zope.interface import Interface

try:
    from zope.interface.interfaces import IObjectEvent
except ImportError:
    # BBB deprecated since 2011 ;)
    from zope.component.interfaces import IObjectEvent


class IUpgradeLayer(Interface):
    """ftw.upgrade specific browser layer.
    """


class IDuringUpgrade(Interface):
    """Request layer to indicate that upgrades are currently executed."""


class IClassMigratedEvent(IObjectEvent):
    """Fired after the class of an object is migrated.

    This event is fired by an UpgradeStep after its migrate_class method is
    called.
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

    def get_profiles():
        """Returns upgrades grouped by done / proposed and assigned profile.

        Example output:
        >>> [{'db_version': u'3',
        ...   'product': 'Products.CMFEditions',
        ...   'description': u'Extension profile for default ' + \
        ...       'CMFEditions setup.',
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
        ...        'done': True,
        ...        'id': '8159946379289711266',
        ...        'sdest': '3'}],
        ...   'path': u'/.../profiles/default',
        ...   'type': 2,
        ...   'id': u'Products.CMFEditions:CMFEditions'}]
        """

    def get_upgrades_by_api_ids(*api_ids):
        """Returns a list of ugprade information dicts for each upgrade which
        is selected with a positional argument.
        The upgrades are ordered in the proposed installation order.
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

    def objects(catalog_query, message, logger=None):
        """Queries the catalog (unrestricted) and an iterator with full
        objects.
        The iterator configures and calls a ``ProgressLogger`` with the
        passed ``message``.
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
        adding ``lines``. The property is expected to be of type "lines".
        If the property does not exist it is created.
        """

    def setup_install_profile(profileid, steps=None):
        """Installs the generic setup profile identified by ``profileid``.
        If a list step names is passed with ``steps`` (e.g. ['actions']),
        only those steps are installed. All steps are installed by default.
        """


class IPostUpgrade(Interface):
    """Post upgrade adapters are called after each time upgrades are
    installed using the ``@@ftw.upgrade`` view.

    Using named adapters allows us to have multiple post upgrade adapters.
    The name should be the name of the profile of the package (e.g.
    "ftw.upgrade:default"), so that ftw.upgrade is able to order the adapters
    using the dependency graph.
    By doing this we assure that adapters integration / policy packages are
    executed at the end.

    The adapter adapts the portal and the request.
    """

    def __init__(portal, request):
        """The adapter adapts portal and request.
        """

    def __call__():
        """Runs the post upgrade adapter.
        """


class IUpgradeStepRecorder(Interface):
    """The upgrade step recorder stores which upgrade steps are installed
    per Plone site.

    This makes it possible to track "orphan" upgrade steps, which were merged
    in after installing upgrade steps with a higher version.
    This can happen with long-term branches when timestamps are used
    as versions.
    """

    def __init__(portal, profilename):
        """The IUpgradeStepRecorder is a multiadapter, adapting the Plone site
        and the profile name (string).
        """

    def mark_as_installed(target_version):
        """Marks an upgrade step as installed.
        The upgrade step is identified with the target version.
        """

    def is_installed(target_version):
        """Returns whether an upgrade step was already installed on this
        Plone site (boolean).
        """


class IRecordableHandler(Interface):
    """Marker interface for upgrade step handlers which support recording
    upgrade step installation (see IUpgradeStepRecorder).
    Marking the upgrade step as installed is done by handlers (upgrade step
    methods or classes) which provide this interface.
    this
    """
