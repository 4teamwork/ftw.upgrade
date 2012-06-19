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

- Install ``ftw.upgrade``s generic setup profile.


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
