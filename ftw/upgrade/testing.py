from ftw.builder.session import BuilderSession
from ftw.builder.testing import BUILDER_LAYER
from ftw.builder.testing import set_builder_session_factory
from path import Path
from pkg_resources import DistributionNotFound
from pkg_resources import get_distribution
from plone.app.testing import applyProfile
from plone.app.testing import FunctionalTesting
from plone.app.testing import IntegrationTesting
from plone.app.testing import PLONE_FIXTURE
from plone.app.testing import PloneSandboxLayer
from plone.app.testing import setRoles, TEST_USER_ID, TEST_USER_NAME, login
from plone.testing import Layer
from plone.testing import z2
from plone.testing import zca
from Products.CMFPlone.utils import getFSVersionTuple
from zope.configuration import xmlconfig
import ftw.upgrade.tests.builders
import logging
import os
import tempfile
import zc.buildout.easy_install
import zc.buildout.testing


def resolve_dependency_versions(pkgname, result=None, extras=()):
    result = result or {}
    if pkgname in result or pkgname in ('setuptools', 'zc.buildout'):
        return result

    try:
        dist = get_distribution(pkgname)
    except DistributionNotFound:
        return result

    result[pkgname] = dist.version
    for pkg in dist.requires(extras):
        resolve_dependency_versions(pkg.project_name, result)

    return result


COMMAND_BUILDOUT_CONFIG = '\n'.join((
        '[buildout]',
        'parts = upgrade',
        '',
        '[upgrade]',
        'recipe = zc.recipe.egg:script',
        'eggs = ftw.upgrade',
        '',
        '[versions]',
        '{versions}'))


class CommandLayer(Layer):

    defaultBases = (BUILDER_LAYER, )

    @property
    def globs(self):
        return self.__dict__

    def setUp(self):
        zc.buildout.testing.buildoutSetUp(self)

        versions = resolve_dependency_versions('ftw.upgrade', extras=['tests'])
        if getFSVersionTuple() < (4, 3):
            resolve_dependency_versions('manuel', versions)
            resolve_dependency_versions('zope.hookable', versions)

        for pkgname in sorted(versions.keys()):
            zc.buildout.testing.install_develop(pkgname, self)

        buildout = COMMAND_BUILDOUT_CONFIG.format(versions='\n'.join(
                '='.join((name, version))
                for (name, version) in versions.items()))
        self.write('buildout.cfg', buildout)

        output = self.system(self.buildout, with_exit_code=True)
        assert output.endswith('EXIT CODE: 0'), 'BUILDOUT FAILED\n\n' + output

        self.upgrade_script_path = os.path.join(self.sample_buildout,
                                                'bin', 'upgrade')

        self.filesystem_snapshot = set(Path(self.sample_buildout).walk())

    def tearDown(self):
        zc.buildout.testing.buildoutTearDown(self)
        pypi_url = 'http://pypi.python.org/simple'
        zc.buildout.easy_install.default_index_url = pypi_url
        os.environ['buildout-testing-index-url'] = pypi_url
        zc.buildout.easy_install._indexes = {}
        logging.shutdown()

    def testTearDown(self):
        for path in (set(Path(self.sample_buildout).walk())
                     - self.filesystem_snapshot):
            if path.isdir():
                path.rmtree()
            if path.isfile():
                path.remove()

    def upgrade_script(self, args, assert_exitcode=True):
        cmd = '{0} {1}'.format(self.upgrade_script_path, args)
        output, exitcode = self.system(
            cmd, with_exit_code=True).split('EXIT CODE: ')
        exitcode = int(exitcode)

        if assert_exitcode:
            assert exitcode == 0, ('Expected exit code 0, got'
                                   ' {0} for "{1}".\nOutput:\n{2}'.format(
                    exitcode, cmd, output))

        return exitcode, output


COMMAND_LAYER = CommandLayer()


def functional_session_factory():
    sess = BuilderSession()
    sess.auto_commit = True
    return sess


class FtwUpgradeLayer(PloneSandboxLayer):

    defaultBases = (PLONE_FIXTURE, BUILDER_LAYER)

    def setUpZope(self, app, configurationContext):
        import Products.CMFPlacefulWorkflow
        xmlconfig.file('configure.zcml', Products.CMFPlacefulWorkflow,
                       context=configurationContext)

        import ftw.upgrade
        xmlconfig.file('configure.zcml', ftw.upgrade,
                       context=configurationContext)

        import ftw.upgrade.tests.profiles
        xmlconfig.file('configure.zcml', ftw.upgrade.tests.profiles,
                       context=configurationContext)

        z2.installProduct(app, 'Products.CMFPlacefulWorkflow')

    def setUpPloneSite(self, portal):
        applyProfile(
            portal, 'Products.CMFPlacefulWorkflow:CMFPlacefulWorkflow')
        applyProfile(portal, 'ftw.upgrade:default')

        setRoles(portal, TEST_USER_ID, ['Manager'])
        login(portal, TEST_USER_NAME)


FTW_UPGRADE_FIXTURE = FtwUpgradeLayer()
FTW_UPGRADE_INTEGRATION_TESTING = IntegrationTesting(
    bases=(FTW_UPGRADE_FIXTURE,), name="FtwUpgrade:Integration")
FTW_UPGRADE_FUNCTIONAL_TESTING = FunctionalTesting(
    bases=(FTW_UPGRADE_FIXTURE,
           set_builder_session_factory(functional_session_factory)),
    name='FtwUpgrade:Functional')


class NewUpgradeLayer(PloneSandboxLayer):
    defaultBases = (PLONE_FIXTURE, BUILDER_LAYER)

    def setUpZope(self, app, configurationContext):
        import Products.CMFPlacefulWorkflow
        xmlconfig.file('configure.zcml', Products.CMFPlacefulWorkflow,
                       context=configurationContext)

        import ftw.upgrade
        xmlconfig.file('configure.zcml', ftw.upgrade,
                       context=configurationContext)

        z2.installProduct(app, 'Products.CMFPlacefulWorkflow')

    def setUpPloneSite(self, portal):
        applyProfile(
            portal, 'Products.CMFPlacefulWorkflow:CMFPlacefulWorkflow')
        applyProfile(portal, 'ftw.upgrade:default')

    def testSetUp(self):
        self['temp_directory'] = Path(tempfile.mkdtemp('ftw.builder'))
        zca.pushGlobalRegistry()
        self['configurationContext'] = zca.stackConfigurationContext(
            self.get('configurationContext'), name='ftw.upgrade')

    def testTearDown(self):
        self['temp_directory'].rmtree_p()
        zca.popGlobalRegistry()


NEW_UPGRADE_LAYER = NewUpgradeLayer()
NEW_UPGRADE_FUNCTIONAL_TESTING = FunctionalTesting(
    bases=(NEW_UPGRADE_LAYER,
           set_builder_session_factory(functional_session_factory)),
    name="ftw.upgrade:functional")
