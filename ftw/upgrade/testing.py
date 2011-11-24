from plone.testing import Layer
from plone.testing import zca
from zope.configuration import xmlconfig
import ftw.upgrade


class UpgradeZCMLLayer(Layer):
    """A layer which only sets up the zcml, but does not start a zope
    instance.
    """

    defaultBases = (zca.ZCML_DIRECTIVES,)

    def testSetUp(self):
        self['configurationContext'] = zca.stackConfigurationContext(
            self.get('configurationContext'))

        xmlconfig.file('meta.zcml', ftw.upgrade,
                       context=self['configurationContext'])

        xmlconfig.file('configure.zcml', ftw.upgrade,
                       context=self['configurationContext'])

    def testTearDown(self):
        del self['configurationContext']


UPGRADE_ZCML_LAYER = UpgradeZCMLLayer()
