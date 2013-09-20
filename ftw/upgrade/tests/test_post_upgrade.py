from Products.CMFCore.utils import getToolByName
from ftw.testing import MockTestCase
from ftw.upgrade.interfaces import IExecutioner
from ftw.upgrade.interfaces import IPostUpgrade
from ftw.upgrade.testing import FTW_UPGRADE_FIXTURE
from mocker import ANY
from plone.app.testing import FunctionalTesting
from plone.app.testing import PloneSandboxLayer
from zope.component import provideAdapter
from zope.component import queryAdapter
from zope.configuration import xmlconfig
from zope.interface import Interface


class UpgradesRegistered(PloneSandboxLayer):

    defaultBases = (FTW_UPGRADE_FIXTURE,)

    def setUpZope(self, app, configurationContext):
        import ftw.upgrade.tests.profiles
        xmlconfig.file('configure.zcml', ftw.upgrade.tests.profiles,
                       context=configurationContext)

        import ftw.upgrade.tests.upgrades
        xmlconfig.file('foo.zcml', ftw.upgrade.tests.upgrades,
                       context=configurationContext)


UPGRADES_REGISTERED = UpgradesRegistered()
UPGRADES_REGISTERED_FUNCTIONAL = FunctionalTesting(
    bases=(UPGRADES_REGISTERED,), name='FtwUpgrade.exec.barbaz:Functional')


class TestPostUpgrade(MockTestCase):

    layer = UPGRADES_REGISTERED_FUNCTIONAL

    def setUp(self):
        super(TestPostUpgrade, self).setUp()
        self.portal_setup = getToolByName(
            self.layer['portal'], 'portal_setup')

        profileid = 'ftw.upgrade.tests.profiles:foo'
        foo_upgrades = self.portal_setup.listUpgrades(profileid)
        self.data = [(profileid, [foo_upgrades[0]['id']])]

    def test_installs_upgrades(self):
        foo_adapter = self.mocker.mock()
        self.expect(foo_adapter(ANY, ANY)())
        self.replay()

        provideAdapter(foo_adapter,
                       adapts=(Interface, Interface),
                       provides=IPostUpgrade,
                       name='ftw.upgrade.tests.profiles:foo')

        executioner = queryAdapter(self.portal_setup, IExecutioner)
        executioner.install(self.data)

    def test_executes_post_upgrades_in_order(self):
        first_adapter_class = self.mocker.mock()
        first_adapter = self.mocker.mock()
        second_adapter_class = self.mocker.mock()
        second_adapter = self.mocker.mock()
        third_adapter_class = self.mocker.mock()
        third_adapter = self.mocker.mock()
        fourth_adapter_class = self.mocker.mock()
        fourth_adapter = self.mocker.mock()

        self.expect(first_adapter_class(ANY, ANY)).result(first_adapter)
        self.expect(second_adapter_class(ANY, ANY)).result(second_adapter)
        self.expect(third_adapter_class(ANY, ANY)).result(third_adapter)
        self.expect(fourth_adapter_class(ANY, ANY)).result(fourth_adapter)

        with self.mocker.order():
            # Assert that the adapters are called in the right order:
            self.expect(first_adapter())
            self.expect(second_adapter())
            self.expect(third_adapter())
            self.expect(fourth_adapter())

        self.replay()

        provideAdapter(fourth_adapter_class,
                       adapts=(Interface, Interface),
                       provides=IPostUpgrade,
                       name='ftw.upgrade.tests.profiles:baz')

        provideAdapter(first_adapter_class,
                       adapts=(Interface, Interface),
                       provides=IPostUpgrade,
                       name='any.package:default')

        provideAdapter(third_adapter_class,
                       adapts=(Interface, Interface),
                       provides=IPostUpgrade,
                       name='ftw.upgrade.tests.profiles:bar')

        provideAdapter(second_adapter_class,
                       adapts=(Interface, Interface),
                       provides=IPostUpgrade,
                       name='ftw.upgrade.tests.profiles:foo')

        executioner = queryAdapter(self.portal_setup, IExecutioner)
        executioner.install(self.data)
