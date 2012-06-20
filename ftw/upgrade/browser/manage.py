from Products.CMFCore.utils import getToolByName
from ftw.upgrade.interfaces import IUpgradeInformationGatherer
from zope.component import getAdapter
from zope.publisher.browser import BrowserView


class ManageUpgrades(BrowserView):

    def get_data(self):
        gstool = getToolByName(self.context, 'portal_setup')
        gatherer = getAdapter(gstool, IUpgradeInformationGatherer)
        return gatherer.get_upgrades()
