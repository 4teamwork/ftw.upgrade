from plone.testing import Layer
from plone.testing import zca
from zope.app.component.hooks import setSite
from zope.component import getSiteManager
from zope.configuration import xmlconfig
from zope.interface import alsoProvides
import ftw.upgrade
import zope.annotation


class DummySite(object):
    getSiteManager = getSiteManager


class UpgradeZCMLLayer(Layer):
    """A layer which only sets up the zcml, but does not start a zope
    instance.
    """

    defaultBases = (zca.ZCML_DIRECTIVES,)

    def testSetUp(self):
        self['configurationContext'] = zca.stackConfigurationContext(
            self.get('configurationContext'))

        xmlconfig.file('configure.zcml', zope.annotation,
                       context=self['configurationContext'])

        xmlconfig.file('meta.zcml', ftw.upgrade,
                       context=self['configurationContext'])

        xmlconfig.file('configure.zcml', ftw.upgrade,
                       context=self['configurationContext'])

        site = DummySite()
        alsoProvides(site, zope.annotation.interfaces.IAttributeAnnotatable)
        setSite(site)

    def testTearDown(self):
        del self['configurationContext']
        setSite(None)


UPGRADE_ZCML_LAYER = UpgradeZCMLLayer()
