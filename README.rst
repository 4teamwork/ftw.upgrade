Introduction
============

This product aims to simplify running and writing third-party Generic Setup
upgrade steps in Plone.

.. figure:: http://onegov.ch/approved.png/image
   :align: right
   :target: http://onegov.ch/community/zertifizierte-module/ftw.upgrade

   Certified: 01/2013

It provides a control panel for running multiple upgrades
at once, based on the upgrade mechanism of Generic Setup (portal_setup).

Further a base class for writing upgrade steps with variety of
helpers for common tasks is provided.


Features
========

* **Managing upgrades**: Provides an advanced view for upgrading
  third-party Plone packages using Generic Setup.
  It allows to upgrade multiple packages at once with an easy to use user
  interface.

* **Writing upgrades**: The package provides a base upgrade class with
  various helpers for tasks often done in upgrades.


Installation
============

- Install ``ftw.upgrade`` by adding it to the list of eggs in your buildout.
  Then run buildout and restart your instance::

    [instance]
    eggs +=
        ftw.upgrade


- Go to Site Setup of your Plone site and activate the ``ftw.upgrade`` add-on.


Manage upgrades
===============

The ``@@manage-upgrades`` view allows to upgrade multiple packages at once:

.. image:: https://github.com/4teamwork/ftw.upgrade/raw/master/docs/manage-upgrades.png



Upgrade step helpers
====================

The ``UpgradeStep`` base class provides various tools and helpers useful
when writing upgrade steps.
It can be used by registering the classmethod directly.
Be aware that the class is very special: it acts like a function and calls
itself automatically.

Example upgrade step definition (defined in a ``upgrades.py``)::

    >>> from ftw.upgrade import UpgradeStep
    >>>
    >>> class UpdateFooIndex(UpgradeStep):
    ...    """The index ``foo`` is a ``FieldIndex`` instead of a
    ...    ``KeywordIndex``. This upgrade step changes the index type
    ...    and reindexes the objects.
    ...    """
    ...
    ...    def __call__(self):
    ..         index_name = 'foo'
    ...        if self.catalog_has_index(index_name):
    ...            self.catalog_remove_index(index_name)
    ...
    ...        self.catalog_add_index(index_name, 'KeywordIndex')
    ...        self.catalog_rebuild_index(index_name)

Registration in ``configure.zcml`` (assume its in the same directory)::

    <configure
        xmlns="http://namespaces.zope.org/zope"
        xmlns:genericsetup="http://namespaces.zope.org/genericsetup"
        i18n_domain="my.package">

        <genericsetup:upgradeStep
            profile="my.package:default"
            source="4"
            destination="5"
            title="Update index 'foo'."
            handler=".upgrades.UpdateFooIndex"
            />

    </configure>


UpgradeStep helper methods
==========================

The ``UpgradeStep`` class has various helper functions:


``self.getToolByName(tool_name)``
    Returns the tool with the name ``tool_name`` of the upgraded site.

``self.catalog_rebuild_index(name)``
    Reindex the ``portal_catalog`` index identified by ``name``.

``self.catalog_reindex_objects(query, idxs=None)``
    Reindex all objects found in the catalog with `query`.
    A list of indexes can be passed as `idxs` for limiting the
    indexed indexes.

``self.catalog_has_index(name)``
    Returns whether there is a catalog index ``name``.

``self.catalog_add_index(name, type_, extra=None)``
    Adds a new index to the ``portal_catalog`` tool.

``self.catalog_remove_index(name)``
    Removes an index to from ``portal_catalog`` tool.

``self.actions_remove_action(category, action_id)``
    Removes an action identified by ``action_id`` from
    the ``portal_actions`` tool from a particulary ``category``.

``self.catalog_unrestricted_get_object(brain)``
    Returns the unrestricted object of a brain.

``self.catalog_unrestricted_search(query, full_objects=False)``
    Searches the catalog without checking security.
    When `full_objects` is `True`, unrestricted objects are
    returned instead of brains.
    Upgrade steps should generally use unrestricted catalog access
    since all objects should be upgraded - even if the manager
    running the upgrades has no access on the objects.

``self.actions_remove_type_action(portal_type, action_id)``
    Removes a ``portal_types`` action from the type identified
    by ``portal_type`` with the action id ``action_id``.

``self.set_property(context, key, value, data_type='string')``
    Set a property with the key ``value`` and the value ``value``
    on the ``context`` safely.
    The property is created with the type ``data_type`` if it does not exist.

``self.add_lines_to_property(context, key, lines)``
    Updates a property with key ``key`` on the object ``context``
    adding ``lines``.
    The property is expected to by of type "lines".
    If the property does not exist it is created.

``self.setup_install_profile(profileid, steps=None)``
    Installs the generic setup profile identified by ``profileid``.
    If a list step names is passed with ``steps`` (e.g. ['actions']),
    only those steps are installed. All steps are installed by default.

``self.migrate_class(obj, new_class)``
    Changes the class of an object. It has a special handling for BTreeFolder2Base
    based containers.


Progress logger
===============

When an upgrade step is taking a long time to complete (e.g. while performing a data migration), the
administrator needs to have information about the progress of the update. It is also important to have
continuous output for avoiding proxy timeouts when accessing Zope through a webserver / proxy.

With the ``ProgressLogger`` context manager it is very easy to log the
progress::

    >>> from ftw.upgrade import ProgressLogger
    >>> from ftw.upgrade import UpgradeStep
    >>>
    >>> class MyUpgrade(UpgradeStep):
    ...
    ...    def __call__(self):
    ...        catalog = self.getToolByName('portal_catalog')
    ...        brains = catalog('MyType')
    ...
    ...        with ProgressLogger('Migrate MyType', brains) as step:
    ...            for brain in brains:
    ...                self.upgrade_obj(brain.getObject())
    ...                step()
    ...
    ...    def upgrade_obj(self, obj):
    ...        do_something_with(obj)


The logger will log the current progress every 5 seconds (default).
Example log output::

    INFO ftw.upgrade STARTING Migrate MyType
    INFO ftw.upgrade 1 of 10 (10%): Migrate MyType
    INFO ftw.upgrade 5 of 50 (50%): Migrate MyType
    INFO ftw.upgrade 10 of 10 (100%): Migrate MyType
    INFO ftw.upgrade DONE: Migrate MyType


IPostUpgrade adapter
====================

By registering an ``IPostUpgrade`` adapter it is possible to run custom code
after running upgrades.
All adapters are executed after each time upgrades were run, not depending on
which upgrades are run.
The name of the adapters should be the profile of the package, so that
``ftw.upgrade`` is able to execute the adapters in order of the GS dependencies.

Example adapter::

    >>> from ftw.upgrade.interfaces import IPostUpgrade
    >>> from zope.interface import implements
    >>>
    >>> class MyPostUpgradeAdapter(object):
    ...     implements(IPostUpgrade)
    ...
    ...     def __init__(self, portal, request):
    ...         self.portal = portal
    ...         self.request = request
    ...
    ...     def __call__(self):
    ...         # custom code, e.g. import a generic setup profile for customizations

Registration in ZCML::

    >>> <configure xmlns="http://namespaces.zope.org/zope">
    ...     <adapter
    ...         factory=".adapters.MyPostUpgradeAdapter"
    ...         provides="ftw.upgrade.interfaces.IPostUpgrade"
    ...         for="Products.CMFPlone.interfaces.siteroot.IPloneSiteRoot
    ...              zope.interface.Interface"
    ...         name="my.package:default" />
    ... </configure>



Links
=====

- Main github project repository: https://github.com/4teamwork/ftw.upgrade
- Issue tracker: https://github.com/4teamwork/ftw.upgrade/issues
- Package on pypi: http://pypi.python.org/pypi/ftw.upgrade
- Continuous integration: https://jenkins.4teamwork.ch/search?q=ftw.upgrade


Copyright
=========

This package is copyright by `4teamwork <http://www.4teamwork.ch/>`_.

``ftw.upgrade`` is licensed under GNU General Public License, version 2.
