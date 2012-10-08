from Acquisition import aq_base, aq_parent
from Products.BTreeFolder2.BTreeFolder2 import BTreeFolder2Base
from Products.CMFCore.utils import getToolByName
from Products.ZCatalog.ProgressHandler import ZLogHandler
from ftw.upgrade.interfaces import IUpgradeStep
from ftw.upgrade.progresslogger import ProgressLogger
from ftw.upgrade.utils import SizedGenerator
from zope.interface import implements
import logging


LOG = logging.getLogger('ftw.upgrade')


class UpgradeStep(object):
    implements(IUpgradeStep)

    def __new__(cls, *args, **kwargs):
        """Let the class act as function since we cannot registry a
        classmethod directly.
        This does call the object immediately after instantiating.
        """
        obj = object.__new__(cls)
        obj.__init__(*args, **kwargs)
        return obj()

    def __init__(self, portal_setup):
        self.portal_setup = portal_setup
        self.portal = self.getToolByName('portal_url').getPortalObject()

    def __call__(self):
        """This method is implemented in each upgrade step with the
        tasks the upgrade should perform.
        """
        raise NotImplementedError()

    def getToolByName(self, tool_name):
        """Returns the tool with the name ``tool_name`` of the upgraded
        site.
        """
        return getToolByName(self.portal_setup, tool_name)

    def catalog_rebuild_index(self, name):
        """Reindex the ``portal_catalog`` index identified by ``name``.
        """
        catalog = self.getToolByName('portal_catalog')
        LOG.info("Reindexing index %s" % name)

        # pylint: disable=W0212
        pgthreshold = catalog._getProgressThreshold() or 100
        # pylint: enable=W0212
        pghandler = ZLogHandler(pgthreshold)
        catalog.reindexIndex(name, None, pghandler=pghandler)

        LOG.info("Reindexing index %s DONE" % name)

    def catalog_reindex_objects(self, query, idxs=None):
        """Reindex all objects found in the catalog with `query`.
        A list of indexes can be passed as `idxs` for limiting the
        indexed indexes.
        """
        if idxs is None:
            idxs = []

        title = '.'.join((self.__module__, self.__class__.__name__))
        objects = self.catalog_unrestricted_search(query, full_objects=True)

        with ProgressLogger(title, objects) as step:
            for obj in objects:
                obj.reindexObject(idxs=idxs)
                step()

    def catalog_has_index(self, name):
        """Returns whether there is a catalog index ``name``.
        """
        catalog = self.getToolByName('portal_catalog')
        index_names = catalog.indexes()
        return name in index_names

    def catalog_add_index(self, name, type_, extra=None):
        """Adds a new index to the ``portal_catalog`` tool.
        """
        catalog = self.getToolByName('portal_catalog')
        return catalog.addIndex(name, type_, extra=extra)

    def catalog_remove_index(self, name):
        """Removes an index to from ``portal_catalog`` tool.
        """
        catalog = self.getToolByName('portal_catalog')
        return catalog.delIndex(name)

    def catalog_unrestricted_get_object(self, brain):
        """Returns the unrestricted object of a brain.
        """
        return self.portal.unrestrictedTraverse(brain.getPath())

    def catalog_unrestricted_search(self, query, full_objects=False):
        """Search catalog without security checks.
        If `full_objects` is `True`, objects instead of brains
        are returned.
        """
        catalog = self.getToolByName('portal_catalog')
        brains = catalog.unrestrictedSearchResults(query)

        if full_objects:
            generator = (self.catalog_unrestricted_get_object(brain)
                         for brain in brains)
            return SizedGenerator(generator, len(brains))

        else:
            return brains

    def actions_remove_action(self, category, action_id):
        """Removes an action identified by ``action_id`` from
        the ``portal_actions`` tool from a particulary ``category``.
        """

        actions_tool = self.getToolByName('portal_actions')
        cat = actions_tool.get(category)

        if cat and action_id in cat:
            del cat[action_id]
            return True

        else:
            return False

    def actions_remove_type_action(self, portal_type, action_id):
        """Removes a ``portal_types`` action from the type identified
        by ``portal_type`` with the action id ``action_id``.
        """
        ttool = self.getToolByName('portal_types')
        fti = ttool.get(portal_type)

        actions = []
        found = False

        for action in fti._actions:  # pylint: disable=W0212
            if action.id != action_id:
                actions.append(action)
            else:
                found = True

        fti._actions = tuple(actions)  # pylint: disable=W0212
        return found

    def set_property(self, context, key, value, data_type='string'):
        """Set a property with the key ``value`` and the value ``value``
        on the ``context`` safely. The property is created with the
        type ``data_type`` if it does not exist.
        """

        # pylint: disable=W0212
        if context.hasProperty(key):
            context._updateProperty(key, value)
        else:
            context._setProperty(key, value, data_type)
        # pylint: enable=W0212

    def add_lines_to_property(self, context, key, lines):
        """Updates a property with key ``key`` on the object ``context``
        adding ``lines``. The property is expected to by of type "lines".
        If the property does not exist it is created.
        """

        if context.hasProperty(key):
            data = list(getattr(context, key))

            if isinstance(lines, (list, tuple)):
                data.extend(lines)
            else:
                data.append(lines)

        elif isinstance(lines, (list, tuple)):
            data = lines

        else:
            data = [lines]

        self.set_property(context, key, data, data_type='lines')

    def setup_install_profile(self, profileid, steps=None):
        """Installs the generic setup profile identified by ``profileid``.
        If a list step names is passed with ``steps`` (e.g. ['actions']),
        only those steps are installed. All steps are installed by default.
        """
        catalog = self.getToolByName('portal_catalog')
        if steps is None:
            catalog.runAllImportStepsFromProfile(profileid, purge_old=False)
        else:
            for step in steps:
                catalog.runImportStepFromProfile(profileid,
                                                 step,
                                                 run_dependencies=False,
                                                 purge_old=False)

    def migrate_class(self, obj, new_class):
        """Changes the class of a object and notifies the container so that
        the change is persistent.
        It has a special handling for BTreeFolder2Base based containers.
        """
        obj.__class__ = new_class

        base = aq_base(obj)
        base._ofs_migrated = True
        base._p_changed = True

        parent = aq_base(aq_parent(obj))
        id_ = base.getId()

        if isinstance(parent, BTreeFolder2Base):
            del parent._tree[id_]
            parent._tree[id_] = base

        else:
            parent._p_changed = True
