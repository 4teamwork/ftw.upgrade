from setuptools import setup, find_packages
import os

version = '1.8.0'

tests_require = [
    'unittest2',
    'mocker',
    'ftw.testing',
    'ftw.testbrowser',
    'ftw.builder',
    'plone.testing',
    'plone.app.testing',

    'zope.configuration',
    'transaction',
    'Products.ATContentTypes',
    'Products.CMFPlacefulWorkflow',
    ]

setup(name='ftw.upgrade',
      version=version,
      description='An upgrade control panel and upgrade '
      'helpers for plone upgrades.',

      long_description=open('README.rst').read() + '\n' +
      open(os.path.join('docs', 'HISTORY.txt')).read(),

      classifiers=[
        'Framework :: Plone',
        'Framework :: Plone :: 4.1',
        'Framework :: Plone :: 4.2',
        'Framework :: Plone :: 4.3',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Programming Language :: Python',
        'Topic :: Software Development',
        ],

      keywords='plone ftw upgrade',
      author='4teamwork GmbH',
      author_email='mailto:info@4teamwork.ch',
      url='https://github.com/4teamwork/ftw.upgrade',
      license='GPL2',

      packages=find_packages(exclude=['ez_setup']),
      namespace_packages=['ftw'],
      include_package_data=True,
      zip_safe=False,

      install_requires=[
        'setuptools',
        'tarjan',

        # Zope
        'AccessControl',
        'Acquisition',
        'transaction',
        'Products.BTreeFolder2',
        'Products.ZCatalog',
        'zope.component',
        'zope.interface',
        'zope.publisher',
        'Zope2',

        # Plone
        'Products.GenericSetup',
        'plone.browserlayer',
        'Products.CMFCore',
        'Products.CMFPlone',
        ],

      tests_require=tests_require,
      extras_require=dict(tests=tests_require),

      entry_points='''
      # -*- Entry points: -*-
      [z3c.autoinclude.plugin]
      target = plone
      ''',
      )
