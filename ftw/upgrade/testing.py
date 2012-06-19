from ftw.testing.layer import ComponentRegistryLayer
from plone.testing import zca


class ZCMLLayer(ComponentRegistryLayer):
    """A layer which only sets up the zcml, but does not start a zope
    instance.
    """

    defaultBases = (zca.ZCML_DIRECTIVES,)

    def setUp(self):
        super(ZCMLLayer, self).setUp()
        import ftw.upgrade.tests
        self.load_zcml_file('test.zcml', ftw.upgrade.tests)


ZCML_LAYER = ZCMLLayer()
