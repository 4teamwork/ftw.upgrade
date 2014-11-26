from BTrees.OOBTree import OOBTree
from ftw.upgrade.interfaces import IUpgradeStepRecorder
from Products.CMFPlone.interfaces import IPloneSiteRoot
from zope.annotation import IAnnotations
from zope.component import adapts
from zope.interface import implements
from zope.interface import Interface


ANNOTATION_KEY = 'ftw.upgrade:recorder'


class UpgradeStepRecorder(object):
    implements(IUpgradeStepRecorder)
    adapts(IPloneSiteRoot, Interface)

    def __init__(self, portal, profilename):
        self.portal = portal
        self.profile = self._normalize_profilename(profilename)
        self.storage = self._get_profile_storage()

    def is_installed(self, target_version):
        return bool(self.storage.get(target_version, False))

    def mark_as_installed(self, target_version):
        self.storage[target_version] = True

    def _get_profile_storage(self):
        annotations = IAnnotations(self.portal)
        if ANNOTATION_KEY not in annotations:
            annotations[ANNOTATION_KEY] = OOBTree()

        if self.profile not in annotations[ANNOTATION_KEY]:
            annotations[ANNOTATION_KEY][self.profile] = OOBTree()

        return annotations[ANNOTATION_KEY][self.profile]

    def _normalize_profilename(self, profilename):
        if profilename.startswith('profile-'):
            profilename = profilename[len('profile-'):]

        if not isinstance(profilename, unicode):
            profilename = profilename.decode('utf-8')

        return profilename
