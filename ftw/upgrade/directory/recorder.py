from BTrees.OOBTree import OOBTree
from ftw.upgrade.interfaces import IUpgradeStepRecorder
from Products.CMFPlone.interfaces import IPloneSiteRoot
from zope.annotation import IAnnotations
from zope.component import adapts
from zope.interface import implementer
from zope.interface import Interface

import six


ANNOTATION_KEY = 'ftw.upgrade:recorder'


@implementer(IUpgradeStepRecorder)
class UpgradeStepRecorder(object):
    adapts(IPloneSiteRoot, Interface)

    def __init__(self, portal, profilename):
        self.portal = portal
        self.profile = self._normalize_profilename(profilename)

    def is_installed(self, target_version):
        storage = self._get_profile_storage()
        return storage and bool(storage.get(target_version, False))

    def mark_as_installed(self, target_version):
        storage = self._get_profile_storage(create=True)
        storage[target_version] = True

    def clear(self):
        self._get_profile_storage(create=True).clear()

    def _get_profile_storage(self, create=False):
        annotations = IAnnotations(self.portal)
        if ANNOTATION_KEY not in annotations and not create:
            return None

        if ANNOTATION_KEY not in annotations:
            annotations[ANNOTATION_KEY] = OOBTree()

        if self.profile not in annotations[ANNOTATION_KEY]:
            annotations[ANNOTATION_KEY][self.profile] = OOBTree()

        return annotations[ANNOTATION_KEY][self.profile]

    def _normalize_profilename(self, profilename):
        if profilename.startswith('profile-'):
            profilename = profilename[len('profile-'):]

        if not isinstance(profilename, six.text_type):
            profilename = profilename.decode('utf-8')

        return profilename
