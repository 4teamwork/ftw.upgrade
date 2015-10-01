from ftw.upgrade.interfaces import IClassMigratedEvent
from zope.component.interfaces import ObjectEvent
from zope.interface import implements


class ClassMigratedEvent(ObjectEvent):

    implements(IClassMigratedEvent)
