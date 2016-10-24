from setuptools import setup, find_packages
import os

version = '2.0.4'

tests_require = [
    'unittest2',
    'mocker',
    'ftw.testing >= 1.8.1',
    'ftw.testbrowser',
    'ftw.builder >= 1.6.0',
    'plone.testing',
    'plone.app.testing',
    'plone.app.intid',
    'plone.app.contenttypes',

    'zope.configuration',
    'zc.recipe.egg',
    'transaction',
    'Products.ATContentTypes',
    'Products.CMFPlacefulWorkflow',
    ]

extras_require = {
    'colors': ['blessed <= 1.9.5'],
    'tests': tests_require}

setup(name='ftw.upgrade',
      version=version,
      description='An upgrade control panel and upgrade '
      'helpers for plone upgrades.',

      long_description=open('README.rst').read() + '\n' +
      open(os.path.join('docs', 'HISTORY.txt')).read(),

      classifiers=[
        'Framework :: Plone',
        'Framework :: Plone :: 4.3',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Programming Language :: Python',
        'Topic :: Software Development',
        ],

      keywords='plone ftw upgrade',
      author='4teamwork AG',
      author_email='mailto:info@4teamwork.ch',
      url='https://github.com/4teamwork/ftw.upgrade',
      license='GPL2',

      packages=find_packages(exclude=['ez_setup']),
      namespace_packages=['ftw'],
      include_package_data=True,
      zip_safe=False,

      install_requires=[
        'argcomplete',
        'argparse',
        'inflection',
        'path.py >= 6.2',
        'requests',
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
        'Plone',
        'Products.GenericSetup',
        'plone.browserlayer',
        'Products.CMFCore',
        'Products.CMFPlone',
        ],

      tests_require=tests_require,
      extras_require=extras_require,

      entry_points={
        'z3c.autoinclude.plugin': [
            'target = plone'],

        'console_scripts': [
            'upgrade = ftw.upgrade.command:main']
        })
