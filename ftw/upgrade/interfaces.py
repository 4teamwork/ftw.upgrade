# pylint: disable=E0211, E0213
# E0211: Method has no argument
# E0213: Method should have "self" as first argument

from zope.interface import Interface, Attribute


class IUpgradeManager(Interface):
    """Utility interface for the upgrade manager.
    """

    def add_upgrade_package(module):
        """Registers a upgrade package.

        Arguments:
        `path` -- Absolute path of the directory.
        """

    def list_upgrades():
        """Returns all upgrades represented as `IUpgradeInfo' objects.
        """

    def install_upgrades(upgrades):
        """Installs a list of upgrades.

        Arguments:
        `upgrades` -- A list of `IUpgradeInfo` objects.
        """

    def is_installed(dottedname):
        """Returns `True` if the class with the dottedname is installed.

        Arguments:
        `dottedname` -- dotted name of the upgrade class.
        """

    def get_upgrade(dottedname):
        """Get a `IUpgradeInfo` object of a specific upgrade by dotted name.
        Returns `None` if there is no such upgrade.

        Arguments:
        `dottedname` -- dotted name of the upgrade class.
        """


class ICatalogMixin(Interface):
    """Mixin for the upgrade manager for supporting and handling catalog
    tasks, such as changing indexes, reindexing or catalog queries.
    """

    def add_catalog_index(name, meta_type, extra=None, index=True):
        """Add a new index to the catalog.

        Arguments:
        `name` -- Name of the index (e.g. "searchable_title").
        `meta_type` -- Type of the index (e.g. "FieldIndex").
        `extra` -- Pass additional parameters to the index.
        `index` -- Reindex index automatically for all types (True).
        """

    def rebuild_catalog_indexes(indexes, query=None, metadata=False):
        """Reindexes one or more indexes for objects returned for a query.
        This task may be hold back until all upgrades have finished. The
        catalog may be not up to date after invoking a rebuild command - it
        is even not up to date in later upgrades.
        It is very important to use `query_catalog` instead of querying the
        catalog directly - this ensures that the result are up to date.

        Arguments:
        `indexes` -- a list of one ore more index names (string)
        `query` -- a regular catalog query (optional)
        `metadata` -- if `True`, the metadata are updated too.
        """

    def query_catalog(query):
        """Query the catalog for some objects. It is very important to not
        use the catalog directly but query it with this method. If a index
        used in the query was requested to be updated but that did not happen
        yet, the index will be updated.
        """

    def finish_catalog_tasks():
        """Finishes all queued catalog update tasks.
        """


class IUpgradeInfo(Interface):
    """Provides information about an upgrade.
    """

    def __init__(upgrade_class):
        """Initializes a upgrade information object for the passed upgrade
        class.

        Arguments:
        `upgrade_class` -- the upgrade class.
        """

    def get_title():
        """Returns the title, which is the dotted name of the class.
        """

    def get_description():
        """Returns the description, which is the docstring of the upgrade
        class.
        """

    def is_installed():
        """Returns `True` if the upgrade is already installed.
        """

    def get_class():
        """Returns the class of the upgrade.
        """

    def get_dependencies():
        """Returns `IUpgradeInfo` objects of all
        """


class IUpgrade(Interface):
    """Markerinterface for every upgrade."""

    dependencies = Attribute(
        'List of dotted names of upgrades which should be run before '
        'this upgrade.')

    def __call__():
        """Runs the upgrade.
        """
