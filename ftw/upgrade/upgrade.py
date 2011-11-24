from ftw.upgrade.interfaces import IUpgrade
from ftw.upgrade.interfaces import IUpgradeManager
from zope.component import getUtility
from zope.interface import implements


class BaseUpgrade(object):
    implements(IUpgrade)

    dependencies = []

    def __init__(self):
        self.manager = getUtility(IUpgradeManager)

    def __call__(self):
        raise NotImplementedError(
            'You have to implement the __call__ method to create an Upgrade')
