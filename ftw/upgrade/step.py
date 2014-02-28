from AccessControl.SecurityInfo import ClassSecurityInformation
from Acquisition import aq_base, aq_parent
from Products.BTreeFolder2.BTreeFolder2 import BTreeFolder2Base
from Products.CMFCore.ActionInformation import ActionInformation
from Products.CMFCore.utils import getToolByName
from Products.ZCatalog.ProgressHandler import ZLogHandler
from ftw.upgrade.helpers import update_security_for
from ftw.upgrade.interfaces import IUpgradeStep
from ftw.upgrade.progresslogger import ProgressLogger
from ftw.upgrade.utils import SizedGenerator
from plone.browserlayer.interfaces import ILocalBrowserLayerType
from zope.interface import directlyProvidedBy
from zope.interface import directlyProvides
from zope.interface import implements
import logging


LOG = logging.getLogger('ftw.upgrade')


class UpgradeStep(object):
    implements(IUpgradeStep)
    security = ClassSecurityInformation()

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

    security.declarePrivate('__call__')
    def __call__(self):
        """This method is implemented in each upgrade step with the
        tasks the upgrade should perform.
        """
        raise NotImplementedError()

    security.declarePrivate('getToolByName')
    def getToolByName(self, tool_name):
        """Returns the tool with the name ``tool_name`` of the upgraded
        site.
        """
        return getToolByName(self.portal_setup, tool_name)

    security.declarePrivate('objects')
    def objects(self, catalog_query, message, logger=None):
        """Queries the catalog (unrestricted) and an iterator with full
        objects.
        The iterator configures and calls a ``ProgressLogger`` with the
        passed ``message``.
        """

        objects = self.catalog_unrestricted_search(
            catalog_query, full_objects=True)

        return ProgressLogger(message, objects, logger=logger)

    security.declarePrivate('catalog_rebuild_index')
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

    security.declarePrivate('catalog_reindex_objects')
    def catalog_reindex_objects(self, query, idxs=None):
        """Reindex all objects found in the catalog with `query`.
        A list of indexes can be passed as `idxs` for limiting the
        indexed indexes.
        """

        title = '.'.join((self.__module__, self.__class__.__name__))

        for obj in self.objects(query, title):
            if idxs is None:
                # Store modification date
                modification_date = obj.modified()
                obj.reindexObject()

                # Restore modification date
                obj.setModificationDate(modification_date)
                obj.reindexObject(idxs=['modified'])

            else:
                obj.reindexObject(idxs=idxs)

    security.declarePrivate('catalog_has_index')
    def catalog_has_index(self, name):
        """Returns whether there is a catalog index ``name``.
        """
        catalog = self.getToolByName('portal_catalog')
        index_names = catalog.indexes()
        return name in index_names

    security.declarePrivate('catalog_add_index')
    def catalog_add_index(self, name, type_, extra=None):
        """Adds a new index to the ``portal_catalog`` tool.
        """
        catalog = self.getToolByName('portal_catalog')
        return catalog.addIndex(name, type_, extra=extra)

    security.declarePrivate('catalog_remove_index')
    def catalog_remove_index(self, name):
        """Removes an index to from ``portal_catalog`` tool.
        """
        catalog = self.getToolByName('portal_catalog')
        return catalog.delIndex(name)

    security.declarePrivate('catalog_unrestricted_get_object')
    def catalog_unrestricted_get_object(self, brain):
        """Returns the unrestricted object of a brain.
        """
        return self.portal.unrestrictedTraverse(brain.getPath())

    security.declarePrivate('catalog_unrestricted_search')
    def catalog_unrestricted_search(self, query, full_objects=False):
        """Search catalog without security checks.
        If `full_objects` is `True`, objects instead of brains
        are returned.
        """
        catalog = self.getToolByName('portal_catalog')
        brains = tuple(catalog.unrestrictedSearchResults(query))

        if full_objects:
            generator = (self.catalog_unrestricted_get_object(brain)
                         for brain in brains)
            return SizedGenerator(generator, len(brains))

        else:
            return brains

    security.declarePrivate('actions_remove_action')
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

    security.declarePrivate('actions_remove_type_action')
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

    security.declarePrivate('actions_add_type_action')
    def actions_add_type_action(self, portal_type, after, action_id, **kwargs):
        """Add a ``portal_type`` action from the type identified
        by ``portal_type``, the position could be definded by the
        ``after`` attribute. If the after action could not be found,
        the action will be inserted at the end of the list."""

        actions = []
        found = False

        ttool = self.getToolByName('portal_types')
        fti = ttool.get(portal_type)

        new_action = ActionInformation(id=action_id, **kwargs)

        for action in fti._actions:  # pylint: disable=W0212
            actions.append(action)
            if action.id == after:
                actions.append(new_action)
                found = True

        if not found:
            actions.append(new_action)

        fti._actions = tuple(actions)  # pylint: disable=W0212

    security.declarePrivate('set_property')
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

    security.declarePrivate('add_lines_to_property')
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

    security.declarePrivate('setup_install_profile')
    def setup_install_profile(self, profileid, steps=None):
        """Installs the generic setup profile identified by ``profileid``.
        If a list step names is passed with ``steps`` (e.g. ['actions']),
        only those steps are installed. All steps are installed by default.
        """
        setup = self.getToolByName('portal_setup')
        if steps is None:
            setup.runAllImportStepsFromProfile(profileid, purge_old=False)
        else:
            for step in steps:
                setup.runImportStepFromProfile(profileid,
                                               step,
                                               run_dependencies=False,
                                               purge_old=False)

    security.declarePrivate('migrate_class')
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

        # Refresh provided interfaces cache
        directlyProvides(base, directlyProvidedBy(base))

    security.declarePrivate('remove_broken_browserlayer')
    def remove_broken_browserlayer(self, name, dottedname):
        """Removes a browser layer registration, whose interface can't be
        imported any more, from the persistent registry.
        """
        iface_name = dottedname.split('.')[-1]
        sm = self.portal.getSiteManager()
        adapters = sm.utilities._adapters
        subscribers = sm.utilities._subscribers

        # Remove adapters ...
        if name in adapters[0][ILocalBrowserLayerType]:
            del adapters[0][ILocalBrowserLayerType][name]

        # ... as well as subscribers
        layer_subscribers = subscribers[0][ILocalBrowserLayerType]
        remaining_layers = tuple([layer for layer in layer_subscribers['']
                                if not layer.__name__ == iface_name])
        layer_subscribers[''] = remaining_layers

        sm.utilities._p_changed = True

    security.declarePrivate('update_security')
    def update_security(self, obj, reindex_security=True):
        """Update the object security and reindex the security indexes in
        the catalog.
        """
        return update_security_for(obj, reindex_security=reindex_security)

    security.declarePrivate('update_workflow_security')
    def update_workflow_security(self, workflow_names, reindex_security=True):
        """Updates the object security of all objects with one of the
        passed workflows.
        `workflows` is expected to be a list of workflow names.
        """

        if getattr(workflow_names, '__iter__', None) is None or \
                isinstance(workflow_names, (str, unicode)):
            raise ValueError(
                '"workflows" must be a list of workflow names.')

        from ftw.upgrade.workflow import WorkflowSecurityUpdater
        updater = WorkflowSecurityUpdater()
        updater.update(workflow_names, reindex_security=reindex_security)
