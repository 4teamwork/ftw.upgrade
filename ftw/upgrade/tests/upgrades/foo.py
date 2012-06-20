from zope.component import provideUtility
from zope.interface import Interface


class IFoo(Interface):
    """Foo utility for testing purpose. Registered on upgrade.
    """


def foo():
    return 'foo is registered'


def register_foo_utility(portal_setup):
    provideUtility(foo, provides=IFoo)
