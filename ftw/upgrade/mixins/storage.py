from ftw.upgrade.interfaces import IStorageMixin
from ftw.upgrade.interfaces import IUpgradeInfo
from ftw.upgrade.interfaces import STORAGE_ANNOTATIONS_KEY
from persistent.dict import PersistentDict
from zope.annotation.interfaces import IAnnotations
from zope.app.component.hooks import getSite
from zope.interface import implements


class StorageMixin(object):

    implements(IStorageMixin)

    def __init__(self):
        self._storage = None

    def _get_storage(self):
        if getattr(self, '_storage', None) is None:
            ann = IAnnotations(getSite())

            if STORAGE_ANNOTATIONS_KEY not in ann:
                ann[STORAGE_ANNOTATIONS_KEY] = PersistentDict()

            self._storage = ann[STORAGE_ANNOTATIONS_KEY]
        return self._storage

    def is_installed(self, dottedname):
        return dottedname in self._get_storage()

    def mark_as_installed(self, upgrade):
        if not IUpgradeInfo.providedBy(upgrade):
            raise ValueError('Expected IUpgradeInfo object, got %s' % (
                    str(upgrade)))

        self._get_storage()[upgrade.get_title()] = True
