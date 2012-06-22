from Products.CMFCore.utils import getToolByName
from Products.ZCatalog.ProgressHandler import ZLogHandler
from ftw.upgrade.interfaces import IUpgradeStep
from zope.interface import implements
import logging


LOG = logging.getLogger('ftw.upgrade')


class UpgradeStep(object):
    implements(IUpgradeStep)

    def __init__(self, portal_setup):
        self.portal_setup = portal_setup
        self.portal = self.getToolByName('portal_url').getPortalObject()

    def __call__(self):
        """This method is implemented in each upgrade step with the
        tasks the upgrade should perform.
        """
        raise NotImplementedError()

    @classmethod
    def upgrade(cls, portal_setup):
        """Runs the upgrade step. This method is registered in ZCML
        as upgrade step handler.
        """
        return cls(portal_setup)()

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

        if context.hasProperty(key):
            context._updateProperty(key, value)  # pylint: disable=W0212
        else:
            context._setProperty(key, value, data_type)  # pylint: disable=W0212

    def add_lines_to_property(self, context, key, lines):
        """Updates a property with key ``key`` on the object ``context``
        adding ``lines``. The property is expected to by of type "lines".
        If the property does not exist it is created.
        """

        if context.hasProperty(key):
            data = getattr(context, key)
            if isinstance(data, tuple):
                data = list(data)

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

    def purge_resource_registries(self):
        """Resets the resource registries ``portal_css``,
        ``portal_javascripts`` and ``portal_kss``.
        """

        jstool = self.getToolByName('portal_javascripts')
        csstool = self.getToolByName('portal_css')
        ksstool = self.getToolByName('portal_kss')

        jstool.clearResources()
        csstool.clearResources()
        ksstool.clearResources()
