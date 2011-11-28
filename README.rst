Introduction
============

This product aims to simplify writing plone upgrade steps. It provides a view
in the plone control panel for running the upgrades.

Upgrades are registered by registering an upgrade package which contains
classes subclassing the `BaseUpgrade` - also subpackages are automatically
scanned.


Usage
=====

Add a dependency from your package to `ftw.upgrade` in `setup.py`:

::

    setup(name='my.package',
          install_requires=[
            'setuptools',
            'ftw.upgrade',
          ])


Register your upgrades package (directory) in `configure.zcml`:

::

    <configure
        xmlns="http://namespaces.zope.org/zope"
        xmlns:upgrade="http://namespaces.zope.org/upgrade">

        <upgrade:registerUpgrades modules=".upgrades" />

    </configure>


Create upgrades somewhere in your upgrades package:

::

    from ftw.upgrade import BaseUpgrade

    class ChangeFoo(BaseUpgrade):
        """There are some objects of content type "Bar" which have a wrong
        foo. Fix this and reindex the index "foo".
        """

        def __call__(self):
            query = {'portal_type': 'Bar', 'foo': 'wrong'}

            for brain in self.manager.query_catalog(query):
                obj = brain.getObject()
                obj.foo = 'fixed'

            self.manager.rebuild_catalog_indexes(
                indexes=['foo'], query=query, metadata=False)


Features
========

* Simple definition of upgrades without registering every single upgrade
* Lazy dependencies between upgrades
* Upgrade control panel
* Upgrades are not bound to versions
* Heavy catalog indexing tasks are queued and merged - this speeds up when
  running multiple upgrades at once
* Save catalog queries with `self.manager.query_catalog`
* Provides tools for common tasks


Links
=====

- Main github project repository: https://github.com/4teamwork/ftw.upgrade
- Issue tracker: https://github.com/4teamwork/ftw.upgrade/issues
- Package on pypi: http://pypi.python.org/pypi/ftw.upgrade


Maintainer
==========

This package is produced and maintained by `4teamwork <http://www.4teamwork.ch/>`_ company.
