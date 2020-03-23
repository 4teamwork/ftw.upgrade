from ftw.upgrade.interfaces import IClassMigratedEvent
from zope.component.interfaces import ObjectEvent
from zope.interface import implementer


@implementer(IClassMigratedEvent)
class ClassMigratedEvent(ObjectEvent):
    pass
