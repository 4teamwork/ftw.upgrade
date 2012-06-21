Introduction
============

This product aims to simplify writing plone upgrade steps. It provides a view
in the plone control panel for running the upgrades.

It is based on the upgrade mechanism of GenericSetup in plone.

Features
========

* **Managing upgrades**: It provides an advanced view for upgrading
  third-party plone packages using Generic Setup.
  It allows to upgrade multiple packages at once with an easy to use user
  interface.

* **Writing upgrades**: The package provides a base upgrade class which has
  various helpers for tasks often done in upgrades.


Installation
============

For using the upgrade view install the ``ftw.upgrade`` using buildout.
Add ``ftw.upgrade`` to the eggs section of your buildout configuration::

    [instance]
    eggs +=
        ftw.upgrade


- Install the generic setup profile of ``ftw.upgrade``.


Upgrade step helpers
====================

The ``UpgradeStep`` base class provides various tools and helpers useful
when writing upgrade steps. It can be used by registering the classmethod
``.upgrade`` as upgrade handler as follows.

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
            handler=".upgrades.UpdateFooIndex.upgrade"
            />

    </configure>


UpgradeStep helper methods
==========================

The ``UpgradeStep`` class has various helper functions:


``self.getToolByName(tool_name)``
    Returns the tool with the name ``tool_name`` of the upgraded
    site.

``self.catalog_rebuild_index(name)``
    Reindex the ``portal_catalog`` index identified by ``name``.

``self.catalog_has_index(name)``
    Returns whether there is a catalog index ``name``.

``self.catalog_add_index(name, type_, extra=None)``
    Adds a new index to the ``portal_catalog`` tool.

``self.catalog_remove_index(name)``
    Removes an index to from ``portal_catalog`` tool.

``self.actions_remove_action(category, action_id)``
    Removes an action identified by ``action_id`` from
    the ``portal_actions`` tool from a particulary ``category``.

``self.actions_remove_type_action(portal_type, action_id)``
    Removes a ``portal_types`` action from the type identified
    by ``portal_type`` with the action id ``action_id``.

``self.set_property(context, key, value, data_type='string')``
    Set a property with the key ``value`` and the value ``value``
    on the ``context`` safely. The property is created with the
    type ``data_type`` if it does not exist.

``self.add_lines_to_property(context, key, lines)``
    Updates a property with key ``key`` on the object ``context``
    adding ``lines``. The property is expected to by of type "lines".
    If the property does not exist it is created.

``self.setup_install_profile(profileid, steps=None)``
    Installs the generic setup profile identified by ``profileid``.
    If a list step names is passed with ``steps`` (e.g. ['actions']),
    only those steps are installed. All steps are installed by default.

``self.purge_resource_registries()``
    Resets the resource registries ``portal_css``,
    ``portal_javascripts`` and ``portal_kss``.


Links
=====

- Main github project repository: https://github.com/4teamwork/ftw.upgrade
- Issue tracker: https://github.com/4teamwork/ftw.upgrade/issues
- Package on pypi: http://pypi.python.org/pypi/ftw.upgrade
- Continuous integration: https://jenkins.4teamwork.ch/search/?q=ftw.upgrade


Copyright
=========

This package is copyright by `4teamwork <http://www.4teamwork.ch/>`_.

``ftw.upgrade`` is licensed under GNU General Public License, version 2.
