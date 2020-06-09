from ftw.upgrade.interfaces import IClassMigratedEvent
from zope.interface import implementer

try:
    from zope.interface.interfaces import ObjectEvent
except ImportError:
    # BBB deprecated since 2011 ;)
    from zope.component.interfaces import ObjectEvent


@implementer(IClassMigratedEvent)
class ClassMigratedEvent(ObjectEvent):
    pass
