from setuptools import setup, find_packages
import os

version = '1.1'

tests_require = [
    'ftw.testing',
    'mocker',
    'plone.app.testing',
    'plone.testing',
    'zope.configuration',
    'unittest2',
    'transaction',
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
        'Products.CMFCore',
        'Products.GenericSetup',
        'plone.browserlayer',
        'zope.component',
        'zope.interface',
        'zope.publisher',

        # 'Products.ZCatalog',  # breaks plone 4.0 compatibilty, since zope 2.12.10 includes it in Zope2 egg.
        'Zope2',
        ],

      tests_require=tests_require,
      extras_require=dict(tests=tests_require),

      entry_points='''
      # -*- Entry points: -*-
      [z3c.autoinclude.plugin]
      target = plone
      ''',
      )
