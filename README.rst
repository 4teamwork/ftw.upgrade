Introduction
============

This product aims to simplify running and writing third-party Generic Setup
upgrade steps in Plone.

It provides a control panel for running multiple upgrades
at once, based on the upgrade mechanism of Generic Setup (portal_setup).

Further a base class for writing upgrade steps with a variety of
helpers for common tasks is provided.

.. contents:: Table of Contents

.. figure:: http://onegov.ch/approved.png/image
   :align: right
   :target: http://onegov.ch/community/zertifizierte-module/ftw.upgrade

   Certified: 01/2013


Features
========

* **Managing upgrades**: Provides an advanced view for upgrading
  third-party Plone packages using Generic Setup.
  It enables upgrading multiple packages at once with an easy to use user
  interface.
  By resolving the dependency graph it is able to optimize the upgrade
  step order so that the upgrade is hassle free.

* **Writing upgrades**: The package provides a base upgrade class with
  various helpers for common upgrade tasks.

* **Upgrade directories with less ZCML**: By registering a directory
  as upgrade-directory, no additional ZCML is needed for each upgrade step.
  By using a timestamp as version number we have less (merge-) conflicts
  and less error potential.

* **Import profile upgrade steps**: Sometimes an upgrade step consists
  solely of importing a purpose-made generic setup profile. A new
  ``upgrade-step:importProfile`` ZCML directive makes this much simpler.


Installation
============

- Install ``ftw.upgrade`` by adding it to the list of eggs in your buildout.
  Then run buildout and restart your instance:

.. code:: ini

    [instance]
    eggs +=
        ftw.upgrade


- Go to Site Setup of your Plone site and activate the ``ftw.upgrade`` add-on.


.. _`console script installation`:

Installing ftw.upgrade's console script
---------------------------------------

If you include ``ftw.upgrade`` in the list of ``eggs`` of a
``plone.recipe.zope2instance`` based section, the ``bin/upgrade`` script
should be generated automatically for you (that is, if you haven't limited or
suppressed script generation via the ``scripts`` option).

Otherwise, installing the console script ``bin/upgrade`` can be done with an
additional buildout part:

.. code:: ini

    [buildout]
    parts += upgrade

    [upgrade]
    recipe = zc.recipe.egg:scripts
    eggs = ftw.upgrade


Compatibility
-------------

Compatible with Plone 4.3.x and 5.1.x.


Manage upgrades
===============

The ``@@manage-upgrades`` view allows to upgrade multiple packages at once:

.. image:: https://github.com/4teamwork/ftw.upgrade/raw/master/docs/manage-upgrades.png


Fallback view
-------------

The ``@@manage-upgrades-plain`` view acts as a fallback view for ``@@manage-upgrades``.
It does not include plone`s main template and thus might be able to render when the default
view fails for some reason.


The bin/upgrade script
======================

Refer to the `console script installation`_ section for instructions on how
to install ``bin/upgrade``.

The ``bin/upgrade`` console script enables management of upgrades on the filesystem
(creating new upgrades, changing upgrade order) as well as interacting with an installed
Plone site, listing profiles and upgrades and installing upgrades.

Some examples:

.. code:: sh

    $ bin/upgrade create "AddCatalogIndex"
    $ bin/upgrade touch my/package/upgrades/20110101000000_add_catalog_index
    $ bin/upgrade sites
    $ bin/upgrade list -s Plone --auth admin:admin --upgrades
    $ bin/upgrade install -s Plone --auth admin:admin  --proposed

The full documentation of the ``bin/upgrade`` script is available using its help system:

.. code:: sh

    $ bin/upgrade help



Upgrade step helpers
====================

The ``UpgradeStep`` base class provides various tools and helpers useful
when writing upgrade steps.
It can be used by registering the classmethod directly.
Be aware that the class is very special: it acts like a function and calls
itself automatically.

Example upgrade step definition (defined in a ``upgrades.py``):

.. code:: python

    from ftw.upgrade import UpgradeStep

    class UpdateFooIndex(UpgradeStep):
       """The index ``foo`` is a ``FieldIndex`` instead of a
       ``KeywordIndex``. This upgrade step changes the index type
       and reindexes the objects.
       """

       def __call__(self):
           index_name = 'foo'
           if self.catalog_has_index(index_name):
               self.catalog_remove_index(index_name)

           self.catalog_add_index(index_name, 'KeywordIndex')
           self.catalog_rebuild_index(index_name)


Registration in ``configure.zcml`` (assuming it's in the same directory):

.. code:: xml

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


Updating objects with progress logging
--------------------------------------

Since an upgrade step often updates a set of objects indexed in the catalog,
there is a useful helper method `self.objects()` which combines querying the
catalog with the `Progress Logger`_.
The catalog is queried unrestricted so that we handle all the objects.

Here is an example for updating all objects of a particular type:

.. code:: python

    from ftw.upgrade import ProgressLogger
    from ftw.upgrade import UpgradeStep

    class ExcludeFilesFromNavigation(UpgradeStep):

       def __call__(self):
           for obj in self.objects({'portal_type': 'File'},
                                   'Enable exclude from navigation for files'):
               obj.setExcludeFromNav(True)


When running the upgrade step you'll be shown a progress log::

    INFO ftw.upgrade STARTING Enable exclude from navigation for files
    INFO ftw.upgrade 1 of 10 (10%): Enable exclude from navigation for files
    INFO ftw.upgrade 5 of 50 (50%): Enable exclude from navigation for files
    INFO ftw.upgrade 10 of 10 (100%): Enable exclude from navigation for files
    INFO ftw.upgrade DONE: Enable exclude from navigation for files



Methods
-------

The ``UpgradeStep`` class has various helper functions:


``self.getToolByName(tool_name)``
    Returns the tool with the name ``tool_name`` of the upgraded site.

``self.objects(catalog_query, message, logger=None, savepoints=None)``
    Queries the catalog (unrestricted) and an iterator with full objects.
    The iterator configures and calls a ``ProgressLogger`` with the
    passed ``message``.

    If set to a non-zero value, the ``savepoints`` argument causes a transaction
    savepoint to be created every n items. This can be used to keep memory usage
    in check when creating large transactions.
    The default value ``None`` indicates that we are not configuring this feature
    and it should use the default configuration, which is usually ``1000``. See
    the `Savepoints`_ section for more details.
    In order to disable savepoints completely, you can use ``savepoints=False``.

    This method will remove matching brains from the catalog when they are broken
    because the object of the brain no longer exists.
    The progress logger will not compensate for the skipped objects and terminate
    before reaching 100%.

``self.catalog_rebuild_index(name)``
    Reindex the ``portal_catalog`` index identified by ``name``.

``self.catalog_reindex_objects(query, idxs=None, savepoints=None)``
    Reindex all objects found in the catalog with `query`.
    A list of indexes can be passed as `idxs` for limiting the
    indexed indexes.
    The ``savepoints`` argument will be passed to ``self.objects()``.

``self.catalog_has_index(name)``
    Returns whether there is a catalog index ``name``.

``self.catalog_add_index(name, type_, extra=None)``
    Adds a new index to the ``portal_catalog`` tool.

``self.catalog_remove_index(name)``
    Removes an index from the ``portal_catalog`` tool.

``self.actions_remove_action(category, action_id)``
    Removes an action identified by ``action_id`` within the given
    ``category`` from the ``portal_actions`` tool.

``self.catalog_unrestricted_get_object(brain)``
    Returns the unrestricted object of a brain.
    Dead brains, for which there is no longer an object, are removed from
    the catalog and ``None`` is returned.

``self.catalog_unrestricted_search(query, full_objects=False)``
    Searches the catalog without checking security.
    When `full_objects` is `True`, unrestricted objects are
    returned instead of brains.
    Upgrade steps should generally use unrestricted catalog access
    since all objects should be upgraded - even if the manager
    running the upgrades has no access on the objects.

    When using ``full_objects``, dead brains, for which there is no longer
    an object, are removed from the catalog and skipped in the generator.
    When dead brains are removed, the resulting sized generator's length
    will not compensate for the skipped objects and therefore be too large.

``self.actions_add_type_action(self, portal_type, after, action_id, **kwargs)``
    Add a ``portal_types`` action from the type identified
    by ``portal_type``, the position can be defined by the
    ``after`` attribute. If the after action can not be found,
    the action will be inserted at the end of the list.

``self.actions_remove_type_action(portal_type, action_id)``
    Removes a ``portal_types`` action from the type identified
    by ``portal_type`` with the action id ``action_id``.

``self.set_property(context, key, value, data_type='string')``
    Safely set a property with the key ``key`` and the value ``value``
    on the given ``context``.
    The property is created with the type ``data_type`` if it does not exist.

``self.add_lines_to_property(context, key, lines)``
    Updates a property with key ``key`` on the object ``context``
    adding ``lines``.
    The property is expected to be of type "lines".
    If the property does not exist it is created.

``self.setup_install_profile(profileid, steps=None)``
    Installs the generic setup profile identified by ``profileid``.
    If a list step names is passed with ``steps`` (e.g. ['actions']),
    only those steps are installed. All steps are installed by default.

``self.ensure_profile_installed(profileid)``
    Install a generic setup profile only when it is not yet installed.

``self.install_upgrade_profile(steps=None)``
    Installs the generic setup profile associated with this upgrade step.
    The profile may be associated to upgrade steps by using either the
    ``upgrade-step:importProfile`` or the ``upgrade-step:directory`` directive.

``self.is_profile_installed(profileid)``
    Checks whether a generic setup profile is installed.
    Respects product uninstallation via quickinstaller.

``self.is_product_installed(product_name)``
    Check whether a product is installed.

``self.uninstall_product(product_name)``
    Uninstalls a product using the quick installer.

``self.migrate_class(obj, new_class)``
    Changes the class of an object. It has a special handling for BTreeFolder2Base
    based containers.

``self.remove_broken_browserlayer(name, dottedname)``
    Removes a browser layer registration whose interface can't be imported any
    more from the persistent registry.
    Messages like these on instance boot time can be an indication of this
    problem:
    ``WARNING OFS.Uninstalled Could not import class 'IMyProductSpecific' from
    module 'my.product.interfaces'``

``self.update_security(obj, reindex_security=True)``
    Update the security of a single object (checkboxes in manage_access).
    This is usefuly in combination with the ``ProgressLogger``.
    It is possible to skip reindexing the object security in the catalog
    (``allowedRolesAndUsers``). This speeds up the update but should only be disabled
    when there are no changes for the ``View`` permission.

``self.update_workflow_security(workflow_names, reindex_security=True, savepoints=None)``
    Update all objects which have one of a list of workflows.
    This is useful when updating a bunch of workflows and you want to make sure
    that the object security is updated properly.

    The update done is kept as small as possible by only searching for
    types which might have this workflow. It does support placeful workflow policies.

    To further speed this up you can pass ``reindex_security=False``, but you need to make
    sure you did not change any security relevant permissions (only ``View`` needs
    ``reindex_security=True`` for default Plone).

    By default, transaction savepoints are created every 1000th object. This prevents
    exaggerated memory consumption when creating large transactions. If your server has
    enough memory, you may turn savepoints off by passing ``savepoints=None``.

``self.base_profile``
    The attribute ``base_profile`` contains the profile name of the upgraded
    profile including the ``profile-`` prefix.
    Example: ``u"profile-the.package:default"``.
    This information is only available when using the
    ``upgrade-step:directory`` directive.

``self.target_version``
    The attribute ``target_version`` contains the target version of the upgrade
    step as a bytestring.
    Example with upgrade step directory: ``"20110101000000"``.
    This information is only available when using the
    ``upgrade-step:directory`` directive.



Progress logger
---------------

When an upgrade step is taking a long time to complete (e.g. while performing a data migration), the
administrator needs to have information about the progress of the update. It is also important to have
continuous output for avoiding proxy timeouts when accessing Zope through a webserver / proxy.

The ``ProgressLogger`` makes logging progress very easy:

.. code:: python

    from ftw.upgrade import ProgressLogger
    from ftw.upgrade import UpgradeStep

    class MyUpgrade(UpgradeStep):

       def __call__(self):
           objects = self.catalog_unrestricted_search(
               {'portal_type': 'MyType'}, full_objects=True)

           for obj in ProgressLogger('Migrate my type', objects):
               self.upgrade_obj(obj)

       def upgrade_obj(self, obj):
           do_something_with(obj)


The logger will log the current progress every 5 seconds (default).
Example log output::

    INFO ftw.upgrade STARTING Migrate MyType
    INFO ftw.upgrade 1 of 10 (10%): Migrate MyType
    INFO ftw.upgrade 5 of 50 (50%): Migrate MyType
    INFO ftw.upgrade 10 of 10 (100%): Migrate MyType
    INFO ftw.upgrade DONE: Migrate MyType


Workflow Chain Updater
----------------------

When the workflow is changed for a content type, the workflow state is
reset to the init state of new workflow for every existing object of this
type. This can be really annoying.

The `WorkflowChainUpdater` takes care of setting every object to the correct
state after changing the chain (the workflow for the type):

.. code:: python

    from ftw.upgrade.workflow import WorkflowChainUpdater
    from ftw.upgrade import UpgradeStep

    class UpdateWorkflowChains(UpgradeStep):

        def __call__(self):
            query = {'portal_type': ['Document', 'Folder']}
            objects = self.catalog_unrestricted_search(
                query, full_objects=True)

            review_state_mapping={
                ('intranet_workflow', 'plone_workflow'): {
                    'external': 'published',
                    'pending': 'pending'}}

            with WorkflowChainUpdater(objects, review_state_mapping):
                # assume that the profile 1002 does install a new workflow
                # chain for Document and Folder.
                self.setup_install_profile('profile-my.package.upgrades:1002')


The workflow chain updater migrates the workflow history by default.
The workflow history migration can be disabled by setting
``migrate_workflow_history`` to ``False``:

.. code:: python

    with WorkflowChainUpdater(objects, review_state_mapping,
                              migrate_workflow_history=False):
        # code


If a transition mapping is provided, the actions in the workflow history
entries are migrated according to the mapping so that the translations
work for the new workflow:

.. code:: python

    transition_mapping = {
        ('intranet_workflow', 'new_workflow'): {
            'submit': 'submit-for-approval'}}

    with WorkflowChainUpdater(objects, review_state_mapping,
                              transition_mapping=transition_mapping):
        # code



Placeful Workflow Policy Activator
----------------------------------

When manually activating a placeful workflow policy all objects with a new
workflow might be reset to the initial state of the new workflow.

ftw.upgrade has a tool for enabling placeful workflow policies without
breaking the review state by mapping it from the old to the new workflows:

.. code:: python

    from ftw.upgrade.placefulworkflow import PlacefulWorkflowPolicyActivator
    from ftw.upgrade import UpgradeStep

    class ActivatePlacefulWorkflowPolicy(UpgradeStep):

        def __call__(self):
            portal_url = self.getToolByName('portal_url')
            portal = portal_url.getPortalObject()

            context = portal.unrestrictedTraverse('path/to/object')

            activator = PlacefulWorkflowPolicyActivator(context)
            activator.activate_policy(
                'local_policy',
                review_state_mapping={
                    ('intranet_workflow', 'plone_workflow'): {
                        'external': 'published',
                        'pending': 'pending'}})

The above example activates a placeful workflow policy recursively on the
object under "path/to/object", enabling the placeful workflow policy
"local_policy".

The mapping then maps the "intranet_workflow" to the "plone_workflow" by
defining which old states (key, intranet_workflow) should be changed to
the new states (value, plone_workflow).

**Options**

- `activate_in`: Activates the placeful workflow policy for the passed in
  object (`True` by default).
- `activate_below`: Activates the placeful workflow policy for the children
  of the passed in object, recursively (`True` by default).
- `update_security`: Update object security and reindex
  allowedRolesAndUsers (`True` by default).


Inplace Migrator
----------------

The inplace migrator provides a fast and easy way for migrating content in
upgrade steps.
It can be used for example to migrate from Archetypes to Dexterity.

The difference between Plone's standard migration and the inplace migration
is that the standard migration creates a new sibling and moves the children
and the inplace migration simply replaces the objects within the tree and
attaches the children to the new parent.
This is a much faster approach since no move / rename events are fired.

Example usage:

.. code:: python

    from ftw.upgrade import UpgradeStep
    from ftw.upgrade.migration import InplaceMigrator

    class MigrateContentPages(UpgradeStep):

        def __call__(self):
            self.install_upgrade_profile()

            migrator = InplaceMigrator(
                new_portal_type='DXContentPage',
                field_mapping={'text': 'content'},
            )

            for obj in self.objects({'portal_type': 'ATContentPage'},
                                    'Migrate content pages to dexterity'):
                migrator.migrate_object(obj)


**Arguments:**

- ``new_portal_type`` (required): The portal_type name of the destination type.
- ``field_mapping``: A mapping of old fieldnames to new fieldnames.
- ``options``: One or many options (binary flags).
- ``ignore_fields``: A list of fields which should be ignored.
- ``attributes_to_migrate``: A list of attributes (not fields!) which should be
  copied from the old to the new object. This defaults to
  ``DEFAULT_ATTRIBUTES_TO_COPY``.

**Options:**

The options are binary flags: multiple options can be or-ed.
Example:

.. code:: python

   from ftw.upgrade.migration import IGNORE_STANDARD_FIELD_MAPPING
   from ftw.upgrade.migration import IGNORE_UNMAPPED_FIELDS
   from ftw.upgrade.migration import InplaceMigrator

    migrator = InplaceMigrator(
        'DXContentPage',
        options=IGNORE_UNMAPPED_FIELDS | IGNORE_STANDARD_FIELD_MAPPING,
    })

- ``DISABLE_FIELD_AUTOMAPPING``: by default, fields with the same name on the
  old and the new implementation are automatically mapped. This flags disables
  the automatic mapping.
- ``IGNORE_UNMAPPED_FIELDS``: by default, a ``FieldsNotMappedError`` is raised
  when unmapped fields are detected. This flags disables this behavior and
  unmapped fields are simply ignored.
- ``BACKUP_AND_IGNORE_UNMAPPED_FIELDS``: ignores unmapped fields but stores the
  values of unmapped fields in the annotations of the new object (using the
  key from the constant ``UNMAPPED_FIELDS_BACKUP_ANN_KEY``), so that the values
  can be handled later. This is useful when having additional fields (schema
  extender).
- ``IGNORE_STANDARD_FIELD_MAPPING`` by default, the ``STANDARD_FIELD_MAPPING``
  is merged into each field mapping, containing standard Plone field mappings
  from Archetypes to Dexterity. This flag disables this behavior.
- ``IGNORE_DEFAULT_IGNORE_FIELDS`` by default, the fields listed in
  ``DEFAULT_IGNORED_FIELDS`` are skipped. This flag disables this behavior.
- ``SKIP_MODIFIED_EVENT`` when `True`, no modified event is triggered.


Upgrade directories
===================

The ``upgrade-step:directory`` ZCML directive allows us to use a new upgrade step
definition syntax with these **advantages**:

- The directory is once registered (ZCML) and automatically scanned at Zope boot time.
  This *reduces the ZCML* used for each upgrade step
  and avoids the redundancy created by having to specify the profile version in multiple places.
- Timestamps are used instead of version numbers.
  Because of that we have *less merge-conflicts*.
- The version in the profile's ``metadata.xml`` is removed and dynamically set
  at Zope boot time to the version of the latest upgrade step.
  We no longer have to maintain this version in upgrades.
- Each upgrade is automatically a Generic Setup profile.
  An instance of the ``UpgradeStep`` class knows which profile it belongs to,
  and that profile can easily be imported with ``self.install_upgrade_profile()``.
  ``self.install_upgrade_profile()``.
- The ``manage-upgrades`` view shows us when we have accidentally merged upgrade steps
  with older timestamps than already executed upgrade steps.
  This helps us detect a long-term-branch merge problem.

Setting up an upgrade directory
-------------------------------

- Register an upgrade directory for your profile (e.g. ``my/package/configure.zcml``):

.. code:: xml

    <configure
        xmlns="http://namespaces.zope.org/zope"
        xmlns:upgrade-step="http://namespaces.zope.org/ftw.upgrade"
        i18n_domain="my.package">

        <include package="ftw.upgrade" file="meta.zcml" />

        <upgrade-step:directory
            profile="my.package:default"
            directory="./upgrades"
            />

    </configure>

- Create the configured upgrade step directory (e.g. ``my/package/upgrades``) and put an
  empty ``__init__.py`` in this directory (prevents some python import warnings).

- Remove the version from the ``metadata.xml`` of the profile for which this upgrade step
  directory is configured (e.g. ``my/package/profiles/default/metadata.xml``):

.. code:: xml

    <?xml version="1.0"?>
    <metadata>
        <dependencies>
            <dependency>profile-other.package:default</dependency>
        </dependencies>
    </metadata>


Declare upgrades soft dependencies
----------------------------------

When having optional dependencies (``extras_require``), we sometimes need to tell
``ftw.upgrade`` that our optional dependency's upgrades needs to be installed
before our upgrades are installed.

We do that by declare a soft dependency in the ``upgrade-step:directory``
directive.
It is possible to declare multiple dependencies by separating them
with whitespace.

.. code:: xml

    <configure
        xmlns="http://namespaces.zope.org/zope"
        xmlns:upgrade-step="http://namespaces.zope.org/ftw.upgrade"
        i18n_domain="my.package">

        <include package="ftw.upgrade" file="meta.zcml" />

        <upgrade-step:directory
            profile="my.package:default"
            directory="./upgrades"
            soft_dependencies="other.package:default
                               collective.fancy:default"
            />

    </configure>


Creating an upgrade step
------------------------

Upgrade steps can be generated with ``ftw.upgrade``'s ``bin/upgrade`` console script.
The idea is to install this script with buildout using
`zc.recipe.egg <https://pypi.org/project/zc.recipe.egg/>`_.

Once installed, upgrade steps can simply be scaffolded with the script:

.. code::

    $ bin/upgrade create AddControlpanelAction

The ``create`` command searches for your ``upgrades`` directory by resolving the
``*.egg-info/top_level.txt`` file. If you have no egg-infos or your upgrades directory is
named differently the automatic discovery does not work and you can provide the
path to the upgrades directory using the ``--path`` argument.

.. sidebar:: Global create-upgrade script

    The
    `create-upgrade <https://github.com/4teamwork/ftw.upgrade/blob/master/scripts/create-upgrade>`_
    script helps you create upgrade steps in any directory (also when not named ``upgrades``).
    Download it and place it somewhere in your ``PATH``, cd into the directory and create an upgrade
    step: ``create-upgrade add_control_panel_action``.

If you would like to have colorized output in the terminal, you can install
the ``colors`` extras (``ftw.upgrade[colors]``).


Reordering upgrade steps
------------------------

The ``bin/upgrade`` console script provides a ``touch`` for reordering generated upgrade steps.
With the optional arguments ``--before`` and ``--after`` upgrade steps can be moved to a specific
position.
When the optional arguments are omitted, the upgrade step timestamp is set to the current time.

Examples:

.. code::

    $ bin/upgrade touch upgrades/20141218093045_add_controlpanel_action
    $ bin/upgrade touch 20141218093045_add_controlpanel_action --before 20141220181500_update_registry
    $ bin/upgrade touch 20141218093045_add_controlpanel_action --after 20141220181500_update_registry



Creating an upgrade step manually
---------------------------------

- Create a directory for the upgrade step in the upgrades directory.
  The directory name must contain a timestamp and a description, concatenated by an underscore,
  e.g. ``YYYYMMDDHHMMII_description_of_what_is_done``:

.. code::

    $ mkdir my/package/upgrades/20141218093045_add_controlpanel_action

- Next, create the upgrade step code in an ``upgrade.py`` in the above directory.
  This file needs to be created, otherwise the upgrade step is not registered.

.. code:: python

    # my/package/upgrades/20141218093045_add_controlpanel_action/upgrade.py

    from ftw.upgrade import UpgradeStep

    class AddControlPanelAction(UpgradeStep):
        """Adds a new control panel action for the package.
        """
        def __call__(self):
            # maybe do something
            self.install_upgrade_profile()
            # maybe do something

..

  - You must inherit from ``UpgradeStep``.
  - Give your class a proper name, although it does not show up anywhere.
  - Add a descriptive docstring to the class, the first consecutive lines are
    used as upgrade step description.
  - Do not forget to execute ``self.install_upgrade_profile()`` if you have Generic Setup based
    changes in your upgrade.

- Put Generic Setup files in the same upgrade step directory, it automatically acts as a
  Generic Setup profile just for this upgrade step.
  The ``install_upgrade_profile`` knows what to import.

  For our example this means we put a file at
  ``my/package/upgrades/20141218093045_add_controlpanel_action/controlpanel.xml``
  which adds the new control panel action.

The resulting directory structure should be something like this:

.. code::

    my/
      package/
        configure.zcml                              # registers the profile and the upgrade directory
        upgrades/                                   # contains the upgrade steps
          __init__.py                               # prevents python import warnings
          20141218093045_add_controlpanel_action/   # our first upgrade step
            upgrade.py                              # should contain an ``UpgradeStep`` subclass
            controlpanel.xml                        # Generic Setup data to import
          20141220181500_update_registry/           # another upgrade step
            upgrade.py
            *.xml
        profiles/
          default/                                  # the default Generic Setup profile
            metadata.xml



Deferrable upgrades
-------------------

Deferrable upgrades are a special type of upgrade that can be omitted on
demand. They still will be proposed and installed by default but can be
excluded from installation by setting a flag.
Deferrable upgrades can be used to decouple upgrades that need not be run right
now, but only eventually, from the critical upgrade path. This can be
particularly useful for long running data migrations or for fix-scripts.

Upgrade-steps can be marked as deferrable by setting a class attribute
``deferrable`` on a subclass of ``UpgradeStep``:

.. code:: python

    # my/package/upgrades/20180709135657_long_running_upgrade/upgrade.py

    from ftw.upgrade import UpgradeStep

    class LongRunningUpgrade(UpgradeStep):
        """Potentially long running upgrade which is deferrable.
        """
        deferrable = True

        def __call__(self):
            pass


When you install upgrades from the command line, you can skip the installation
of deferred upgrade steps with:

.. code:: sh

    $ bin/upgrade install -s plone --proposed --skip-deferrable


When you install upgrades with the ``@@manage-upgrades`` view, deferrable
upgrade steps show an additional icon and can be deselected manually.


JSON API
========

The JSON API allows to get profiles and upgrades for a Plone site and execute upgrades.


Authentication and authorization
--------------------------------

The API is available for users with the "cmf.ManagePortal" permission, usually the "Manager"
role is required.


Versioning
----------

A specific API version can be requested by adding the version to the URL. Example:

.. code:: sh

    $ curl -uadmin:admin http://localhost:8080/upgrades-api/v1/list_plone_sites


API Discovery
-------------

The API is discoverable and self descriptive.
The API description is returned when the API action is omitted:


.. code:: sh

    $ curl -uadmin:admin http://localhost:8080/upgrades-api/
    {
        "api_version": "v1",
        "actions": [
            {
                "request_method": "GET",
                "required_params": [],
                "name": "current_user",
                "description": "Return the current user when authenticated properly. This can be used for testing authentication."
            },
            {
                "request_method": "GET",
                "required_params": [],
                "name": "list_plone_sites",
                "description": "Returns a list of Plone sites."
            }
        ]
    }

    $ curl -uadmin:admin http://localhost:8080/Plone/upgrades-api/
    ...




Listing Plone sites:
--------------------

.. code:: sh

    $ curl -uadmin:admin http://localhost:8080/upgrades-api/list_plone_sites
    [
        {
            "path": "/Plone",
            "id": "Plone",
            "title": "Website"
        }
    ]


Listing profiles and upgrades
-----------------------------

List all profiles
~~~~~~~~~~~~~~~~~

Listing all installed Generic Setup profiles with upgrades for a Plone site:

.. code:: sh

    $ curl -uadmin:admin http://localhost:8080/Plone/upgrades-api/list_profiles
    [
        {
            "id": "Products.CMFEditions:CMFEditions",
            "db_version": "4",
            "product": "Products.CMFEditions",
            "title": "CMFEditions",
            "outdated_fs_version": false,
            "fs_version": "4",
            "upgrades": [
                {
                    "proposed": false,
                    "title": "Fix portal_historyidhandler",
                    "outdated_fs_version": false,
                    "orphan": false,
                    "deferred": false,
                    "dest": "3",
                    "done": true,
                    "source": "2.0",
                    "id": "3@Products.CMFEditions:CMFEditions"
                },

    ...

Get a profile
~~~~~~~~~~~~~

Listing a single profile and its upgrades:

.. code:: sh

    $ curl -uadmin:admin "http://localhost:8080/Plone/upgrades-api/get_profile?profileid=Products.TinyMCE:TinyMCE"
    {
        "id": "Products.TinyMCE:TinyMCE",
        "db_version": "7",
        "product": "Products.TinyMCE",
        "title": "TinyMCE Editor Support",
        "outdated_fs_version": false,
        "fs_version": "7",
        "upgrades": [
            {
                "proposed": false,
                "title": "Upgrade TinyMCE",
                "outdated_fs_version": false,
                "orphan": false,
                "deferred": false,
                "dest": "1.1",
                "done": true,
                "source": "1.0",
                "id": "1.1@Products.TinyMCE:TinyMCE"
            },
    ...


List proposed profiles
~~~~~~~~~~~~~~~~~~~~~~

Listing all profiles proposing upgrades, each profile only including upgrades which
are propsosed:

.. code:: sh

    $ curl -uadmin:admin http://localhost:8080/Plone/upgrades-api/list_profiles_proposing_upgrades
    ...


List proposed upgrades
~~~~~~~~~~~~~~~~~~~~~~

Listing all proposed upgrades without the wrapping profile infos:

.. code:: sh

    $ curl -uadmin:admin http://localhost:8080/Plone/upgrades-api/list_proposed_upgrades
    [
        {
            "proposed": true,
            "title": "Foo.",
            "outdated_fs_version": false,
            "orphan": true,
            "deferred": false,
            "dest": "20150114104527",
            "done": false,
            "source": "10000000000000",
            "id": "20150114104527@ftw.upgrade:default"
        }
    ]


Executing upgrades
------------------

When executing upgrades the response is not of type JSON but a streamed upgrade log.
If the request is correct, the response status will always be 200 OK, no matter whether
the upgrades will install correctly or not.
If an upgrade fails, the request and the transaction is aborted and the response content
will end with "Result: FAILURE\n".
If the upgrade succeeds, the response content will end with "Result: SUCCESS\n".


Executing selected upgrades
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Selected upgrades can be executed by their API-ID (format: "<dest>@<profileid>").
When upgrade groups are used the API-ID is kind of ambiguous and identifies / installs all
upgrade steps of the same profile with the same target version.

All upgrade steps are reordered to the installation order proposed by ftw.upgrade.
It is not possible to change the order within one request, use multiple requests for
unproposed installation order.
The installation order is done by topogically ordering the profiles by their dependencies
and ordering the upgrades within each profile by their target version.

Example for executing a selected set of upgrades:

.. code:: sh

    $ curl -uadmin:admin -X POST "http://localhost:8080/Plone/upgrades-api/execute_upgrades?upgrades:list=7@Products.TinyMCE:TinyMCE&upgrades:list=20150114104527@ftw.upgrade:default"
    2015-01-14 11:16:14 INFO ftw.upgrade ______________________________________________________________________
    2015-01-14 11:16:14 INFO ftw.upgrade UPGRADE STEP Products.TinyMCE:TinyMCE: Upgrade TinyMCE 1.3.4 to 1.3.5
    2015-01-14 11:16:14 INFO ftw.upgrade Ran upgrade step Upgrade TinyMCE 1.3.4 to 1.3.5 for profile Products.TinyMCE:TinyMCE
    2015-01-14 11:16:14 INFO ftw.upgrade Upgrade step duration: 1 second
    2015-01-14 11:16:14 INFO ftw.upgrade ______________________________________________________________________
    2015-01-14 11:16:14 INFO ftw.upgrade UPGRADE STEP ftw.upgrade:default: Foo.
    2015-01-14 11:16:14 INFO GenericSetup.rolemap Role / permission map imported.
    2015-01-14 11:16:14 INFO GenericSetup.archetypetool Archetype tool imported.
    2015-01-14 11:16:14 INFO ftw.upgrade Ran upgrade step Foo. for profile ftw.upgrade:default
    2015-01-14 11:16:14 INFO ftw.upgrade Upgrade step duration: 1 second
    Result: SUCCESS


Execute all proposed upgrades
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Example for executing all proposed upgrades of a Plone site:

.. code:: sh

    $ curl -uadmin:admin -X POST http://localhost:8080/Plone/upgrades-api/execute_proposed_upgrades
    2015-01-14 11:17:34 INFO ftw.upgrade ______________________________________________________________________
    2015-01-14 11:17:34 INFO ftw.upgrade UPGRADE STEP ftw.upgrade:default: Bar.
    2015-01-14 11:17:35 INFO GenericSetup.rolemap Role / permission map imported.
    2015-01-14 11:17:35 INFO GenericSetup.archetypetool Archetype tool imported.
    2015-01-14 11:17:35 INFO ftw.upgrade Ran upgrade step Bar. for profile ftw.upgrade:default
    2015-01-14 11:17:35 INFO ftw.upgrade Upgrade step duration: 1 second
    Result: SUCCESS


Installing profiles
~~~~~~~~~~~~~~~~~~~

You can install complete profiles.  When the profile is already
installed, nothing is done.  Usually you will want to install the
default profile, but it is fine to install an uninstall profile.

Note that we do nothing with the ``portal_quickinstaller``.  So if you
install an uninstall profile, you may still see the product as
installed.  But for default profiles everything works as you would
expect.

Example for installing PloneFormGen (which was not installed yet) and
ftw.upgrade (which was already installed):

.. code:: sh

    $ curl -uadmin:admin -X POST "http://localhost:8080/Plone/upgrades-api/execute_profiles?profiles:list=Products.PloneFormGen:default&profiles:list=ftw.upgrade:default"
    2016-01-05 13:09:46 INFO ftw.upgrade Installing profile Products.PloneFormGen:default.
    2016-01-05 13:09:46 INFO GenericSetup.rolemap Role / permission map imported.
    ...
    2016-01-05 13:09:48 INFO GenericSetup.types 'FieldsetEnd' type info imported.
    2016-01-05 13:09:48 INFO GenericSetup.factorytool FactoryTool settings imported.
    2016-01-05 13:09:48 INFO ftw.upgrade Done installing profile Products.PloneFormGen:default.
    2016-01-05 13:09:48 INFO ftw.upgrade Ignoring already installed profile ftw.upgrade:default.
    Result: SUCCESS

By default, already installed profiles are skipped.
When supplying the ``force_reinstall=True`` request parameter,
already installed profiles will be reinstalled.


Upgrading Plone
~~~~~~~~~~~~~~~

You can migrate your Plone Site.  This is what you would manually do
in the @@plone-upgrade view, which is linked to in the overview
control panel (or the ZMI) when your Plone Site needs updating.

Example for upgrading Plone:

.. code:: sh

    $ curl -uadmin:admin -X POST "http://localhost:8080/test/upgrades-api/plone_upgrade"
    "Plone Site has been updated."

Example for upgrading Plone when no upgrade is needed:

.. code:: sh

    $ curl -uadmin:admin -X POST "http://localhost:8080/test/upgrades-api/plone_upgrade"
    "Plone Site was already up to date."

For checking whether a Plone upgrade is needed, you can do:

.. code:: sh

    $ curl -uadmin:admin -X POST "http://localhost:8080/test/upgrades-api/plone_upgrade_needed"


Recook resources
----------------

CSS and JavaScript resource bundles can be recooked:

.. code:: sh

    $ curl -uadmin:admin -X POST http://localhost:8080/Plone/upgrades-api/recook_resources
    "OK"


Combine bundles
---------------

CSS and JavaScript bundles can be combined:

.. code:: sh

    $ curl -uadmin:admin -X POST http://localhost:8080/Plone/upgrades-api/combine_bundles
    "OK"

This is for Plone 5 or higher.
This runs the same code that runs when you import a profile that makes changes in the resource registries.


Import-Profile Upgrade Steps
============================

Sometimes an upgrade step consists solely of importing a purpose-made generic setup
profile. Creating such upgrade steps are often much simpler than doing
the change in python, because we can simply copy the necessary parts of the new
default generic setup profile into the upgrade step profile.

Normally to do this, we would have to register an upgrade step and a Generic Setup
profile and write an upgrade step handler importing the profile.

ftw.upgrade makes this much simpler by providing an ``importProfile`` ZCML directive
specifically for this use case.

Example ``configure.zcml`` meant to be placed in your ``upgrades`` sub-package:

.. code:: xml

    <configure
        xmlns="http://namespaces.zope.org/zope"
        xmlns:upgrade-step="http://namespaces.zope.org/ftw.upgrade"
        i18n_domain="my.package">

        <include package="ftw.upgrade" file="meta.zcml" />

        <upgrade-step:importProfile
            title="Update email_from_address"
            profile="my.package:default"
            source="1007"
            destination="1008"
            directory="profiles/1008"
            />

    </configure>

This example upgrade step updates the ``email_from_address`` property.

A generic setup profile is automatically registered and hooked up with the
generated upgrade step handler.

Simply put a ``properties.xml`` in the folder ``profiles/1008`` relative to the
above ``configure.zcml`` and the upgrade step is ready for deployment.

Optionally, a ``handler`` may be defined.
The handler, a subclass of ``UpgradeStep``, can import the associated generic
setup profile with ``self.install_upgrade_profile()``.



IPostUpgrade adapter
====================

By registering an ``IPostUpgrade`` adapter it is possible to run custom code
after running upgrades.
All adapters are executed after each time upgrades were run, regardless of
which upgrades are run.
The name of the adapters should be the profile of the package, so that
``ftw.upgrade`` is able to execute the adapters in order of the GS dependencies.

Example adapter:

.. code:: python

    from ftw.upgrade.interfaces import IPostUpgrade
    from zope.interface import implements

    class MyPostUpgradeAdapter(object):
        implements(IPostUpgrade)

        def __init__(self, portal, request):
            self.portal = portal
            self.request = request

        def __call__(self):
            # custom code, e.g. import a generic setup profile for customizations

Registration in ZCML:

.. code:: xml

    <configure xmlns="http://namespaces.zope.org/zope">
        <adapter
            factory=".adapters.MyPostUpgradeAdapter"
            provides="ftw.upgrade.interfaces.IPostUpgrade"
            for="Products.CMFPlone.interfaces.siteroot.IPloneSiteRoot
                 zope.interface.Interface"
            name="my.package:default" />
    </configure>


Savepoints
==========

Certain iterators of ``ftw.upgrade`` are wrapped with a ``SavepointIterator``,
creating savepoints after each batch of items.
This allows us to keep the memory footprint low.

The threshold for the savepoint iterator can be passed to certain methods, such as
``self.objects`` in an upgrade, or it can be configured globally with an environment variable:

.. code::

  UPGRADE_SAVEPOINT_THRESHOLD = 1000

The default savepoint threshold is 1000.

Memory optimization while running upgrades
==========================================

Zope is optimized for executing many smaller requests.
The ZODB pickle cache keeps objects in the memory, so that they can be used for the next
request.

Running a large upgrade is a long-running request though, increasing the chance of a
memory problem.

``ftw.upgrade`` tries to optimize the memory usage by creating savepoints and triggering
the pickle cache garbage collector.

In order for this to work properly you should configure your ZODB cache sizes correctly
(`zodb-cache-size-bytes` or `zodb-cache-size`).


Prevent ftw.upgrade from marking upgrades as installed
======================================================

``ftw.upgrade`` automatically marks all upgrade steps of a profile as installed when
the full profile is imported. This is important for the initial installation.

In certain situations you may want to import the profile but not mark the upgrade steps
as installed. For example this could be done in a big migration project where the default
migration path cannot be followed.

You can do that like this for all generic setup profiles:

.. code:: python

    from ftw.upgrade.directory.subscribers import no_upgrade_step_marking

    with no_upgrade_step_marking():
        # install profile with portal_setup

or for certain generic setup profiles:

.. code:: python

    from ftw.upgrade.directory.subscribers import no_upgrade_step_marking

    with no_upgrade_step_marking('my.package:default'):
        # install profile with portal_setup



Links
=====

- Github: https://github.com/4teamwork/ftw.upgrade
- Issues: https://github.com/4teamwork/ftw.upgrade/issues
- Pypi: https://pypi.org/project/ftw.upgrade/
- Continuous integration: https://jenkins.4teamwork.ch/search?q=ftw.upgrade


Copyright
=========

This package is copyright by `4teamwork <http://www.4teamwork.ch/>`_.

``ftw.upgrade`` is licensed under GNU General Public License, version 2.
