from ftw.testing.layer import ComponentRegistryLayer
from plone.testing import zca
from zope.annotation.interfaces import IAttributeAnnotatable
from zope.app.component.hooks import setSite
from zope.component import getSiteManager as sm
from zope.interface import implements


class DummySite(object):
    implements(IAttributeAnnotatable)

    getSiteManager = sm


class UpgradeZCMLLayer(ComponentRegistryLayer):
    """A layer which only sets up the zcml, but does not start a zope
    instance.
    """

    defaultBases = (zca.ZCML_DIRECTIVES,)

    def setUp(self):
        super(UpgradeZCMLLayer, self).setUp()
        import ftw.upgrade.tests
        self.load_zcml_file('test.zcml', ftw.upgrade.tests)

    def testSetUp(self):
        super(UpgradeZCMLLayer, self).testSetUp()
        site = DummySite()
        setSite(site)

    def testTearDown(self):
        super(UpgradeZCMLLayer, self).testTearDown()
        setSite(None)


UPGRADE_ZCML_LAYER = UpgradeZCMLLayer()
