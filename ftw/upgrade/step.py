from AccessControl.SecurityInfo import ClassSecurityInformation
from Acquisition import aq_base
from Acquisition import aq_parent
from ftw.upgrade.events import ClassMigratedEvent
from ftw.upgrade.exceptions import NoAssociatedProfileError
from ftw.upgrade.helpers import update_security_for
from ftw.upgrade.interfaces import IUpgradeStep
from ftw.upgrade.progresslogger import ProgressLogger
from ftw.upgrade.utils import log_silencer
from ftw.upgrade.utils import SavepointIterator
from ftw.upgrade.utils import SizedGenerator
from plone.browserlayer.interfaces import ILocalBrowserLayerType
from plone.portlets.interfaces import IPortletManager
from plone.portlets.interfaces import IPortletManagerRenderer
from Products.BTreeFolder2.BTreeFolder2 import BTreeFolder2Base
from Products.CMFCore.ActionInformation import ActionInformation
from Products.CMFCore.utils import getToolByName
from Products.ZCatalog.ProgressHandler import ZLogHandler
from zExceptions import NotFound
from zope.browser.interfaces import IBrowserView
from zope.event import notify
from zope.interface import directlyProvidedBy
from zope.interface import directlyProvides
from zope.interface import implementer
from zope.interface import Interface
from zope.publisher.interfaces.browser import IBrowserRequest

import logging
import re
import six


try:
    from Products.GenericSetup.tool import DEPENDENCY_STRATEGY_NEW
except ImportError:
    DEPENDENCY_STRATEGY_NEW = None

try:
    from Products.CMFPlone.utils import get_installer
except ImportError:
    get_installer = None


LOG = logging.getLogger('ftw.upgrade')


@implementer(IUpgradeStep)
class UpgradeStep(object):
    security = ClassSecurityInformation()

    deferrable = False

    def __new__(cls, *args, **kwargs):
        """Let the class act as function since we cannot registry a
        classmethod directly.
        This does call the object immediately after instantiating.
        """
        obj = object.__new__(cls)
        obj.__init__(*args, **kwargs)
        return obj()

    def __init__(self, portal_setup,
                 associated_profile=None,
                 base_profile=None,
                 target_version=None):
        self.portal_setup = portal_setup
        self.portal = self.getToolByName('portal_url').getPortalObject()
        self.associated_profile = associated_profile
        self.base_profile = base_profile
        self.target_version = target_version

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
    def objects(self, catalog_query, message, logger=None,
                savepoints=None):
        """Queries the catalog (unrestricted) and an iterator with full
        objects.
        The iterator configures and calls a ``ProgressLogger`` with the
        passed ``message``.
        """

        objects = self.catalog_unrestricted_search(
            catalog_query, full_objects=True)

        objects = SavepointIterator.build(objects, savepoints, logger)
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
    def catalog_reindex_objects(self, query, idxs=None, savepoints=None):
        """Reindex all objects found in the catalog with `query`.
        A list of indexes can be passed as `idxs` for limiting the
        indexed indexes.
        """

        title = '.'.join((self.__module__, self.__class__.__name__))

        for obj in self.objects(query, title, savepoints=savepoints):
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
        try:
            return self.portal.unrestrictedTraverse(brain.getPath())
        except (AttributeError, KeyError, NotFound):
            LOG.warning('The object of the brain with rid {!r} no longer'
                        ' exists at the path {!r}; removing the brain.'.format(
                            brain.getRID(), brain.getPath()))
            catalog = self.getToolByName('portal_catalog')
            catalog.uncatalog_object(brain.getPath())
            return None

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
            generator = (obj for obj in generator if obj is not None)
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
        """Add a ``portal_types`` action from the type identified
        by ``portal_type``, the position can be defined by the
        ``after`` attribute. If the after action can not be found,
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
        adding ``lines``. The property is expected to be of type "lines".
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
    def setup_install_profile(self, profileid, steps=None,
                              dependency_strategy=None):
        """Installs the generic setup profile identified by ``profileid``.
        If a list step names is passed with ``steps`` (e.g. ['actions']),
        only those steps are installed. All steps are installed by default.
        """
        setup = self.getToolByName('portal_setup')
        if steps is None:
            runargs = {'purge_old': False}
            if DEPENDENCY_STRATEGY_NEW is not None:
                runargs['dependency_strategy'] = (
                    dependency_strategy or DEPENDENCY_STRATEGY_NEW)

            setup.runAllImportStepsFromProfile(profileid, **runargs)
        else:
            for step in steps:
                setup.runImportStepFromProfile(profileid,
                                               step,
                                               run_dependencies=False,
                                               purge_old=False)

    security.declarePrivate('ensure_profile_installed')
    def ensure_profile_installed(self, profileid):
        """Install a generic setup profile only when it is not yet installed.
        """
        if not self.is_profile_installed(profileid):
            self.setup_install_profile(profileid)

    security.declarePrivate('install_upgrade_profile')
    def install_upgrade_profile(self, steps=None):
        """Installs the generic setup profile for this upgrade step.
        """
        if self.associated_profile is None:
            raise NoAssociatedProfileError()

        self.setup_install_profile(self.associated_profile, steps=steps)

    security.declarePrivate('is_product_installed')
    def is_profile_installed(self, profileid):
        """Checks whether a generic setup profile is installed.
        Respects product uninstallation via quickinstaller.
        """
        profileid = re.sub(r'^profile-', '', profileid)

        try:
            profileinfo = self.portal_setup.getProfileInfo(profileid)
        except KeyError:
            return False

        if not self.is_product_installed(profileinfo['product']):
            return False

        version = self.portal_setup.getLastVersionForProfile(profileid)
        return version != 'unknown'

    security.declarePrivate('is_product_installed')
    def is_product_installed(self, product_name):
        """Check whether a product is installed.
        """
        if get_installer is not None:
            quickinstaller = get_installer(self.portal, self.portal.REQUEST)
            return (quickinstaller.is_product_installable(product_name)
                    and quickinstaller.is_product_installed(product_name))
        else:
            quickinstaller = self.getToolByName('portal_quickinstaller')
            return (quickinstaller.isProductInstallable(product_name)
                    and quickinstaller.isProductInstalled(product_name))


    security.declarePrivate('uninstall_product')
    def uninstall_product(self, product_name):
        """Uninstalls a product using the quick installer.
        """
        if get_installer is not None:
            quickinstaller = get_installer(self.portal, self.portal.REQUEST)
            quickinstaller.uninstall_product(product_name)
        else:
            quickinstaller = self.getToolByName('portal_quickinstaller')
            quickinstaller.uninstallProducts([product_name])

    security.declarePrivate('migrate_class')
    def migrate_class(self, obj, new_class):
        """Changes the class of a object and notifies the container so that
        the change is persistent.
        It has a special handling for BTreeFolder2Base based containers.

        Fires an event after class migration so that custom reference cleanup
        can be performed.
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

        notify(ClassMigratedEvent(obj))

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

        sm._utility_registrations.pop((ILocalBrowserLayerType, name), None)

        sm.utilities._p_changed = True

    security.declarePrivate('remove_broken_portlet_manager')
    def remove_broken_portlet_manager(self, name):
        """Removes a portlet manager, that cannot be imported any more, from
        the persistent registry.

        This method also filters some pretty ugly error messages from the
        zodb connection log. The errors would appear when zodb attempts to load
        the objects for classes that have been uninstalled previously.
        """
        sm = self.portal.getSiteManager()

        manager_renderer = sm.adapters.lookup(
            [Interface, IBrowserRequest, IBrowserView],
            IPortletManagerRenderer,
            name)
        if manager_renderer is not None:
            with log_silencer("ZODB.Connection", "Couldn't load state for"):
                sm.unregisterAdapter(
                    manager_renderer,
                    [Interface, IBrowserRequest, IBrowserView],
                    IPortletManagerRenderer,
                    name)
            LOG.info("Removed portlet manager renderer {0}".format(name))

        with log_silencer("ZODB.Connection", "Couldn't load state for"):
            manager = sm.queryUtility(IPortletManager, name=name)
            if manager is not None:
                sm.unregisterUtility(component=manager,
                                     name=name,
                                     provided=IPortletManager)
                LOG.info("Removed portlet manager {0}".format(name))

    security.declarePrivate('update_security')
    def update_security(self, obj, reindex_security=True):
        """Update the object security and reindex the security indexes in
        the catalog.
        """
        return update_security_for(obj, reindex_security=reindex_security)

    security.declarePrivate('update_workflow_security')
    def update_workflow_security(self, workflow_names, reindex_security=True,
                                 savepoints=1000):
        """Updates the object security of all objects with one of the
        passed workflows.
        `workflows` is expected to be a list of workflow names.
        If `savepoints` is None, no savepoints will be created.
        """

        if getattr(workflow_names, '__iter__', None) is None or \
                isinstance(workflow_names, (str, six.text_type)):
            raise ValueError(
                '"workflows" must be a list of workflow names.')

        from ftw.upgrade.workflow import WorkflowSecurityUpdater
        updater = WorkflowSecurityUpdater()
        updater.update(workflow_names, reindex_security=reindex_security,
                       savepoints=savepoints)
