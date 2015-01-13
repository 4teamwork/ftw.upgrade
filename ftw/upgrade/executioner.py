from AccessControl.SecurityInfo import ClassSecurityInformation
from ftw.upgrade.interfaces import IExecutioner
from ftw.upgrade.interfaces import IPostUpgrade
from ftw.upgrade.interfaces import IUpgradeInformationGatherer
from ftw.upgrade.transactionnote import TransactionNote
from ftw.upgrade.utils import format_duration
from ftw.upgrade.utils import get_sorted_profile_ids
from Products.CMFCore.utils import getToolByName
from Products.GenericSetup.interfaces import ISetupTool
from Products.GenericSetup.upgrade import _upgrade_registry
from zope.component import adapts
from zope.component import getAdapters
from zope.interface import implements
import logging
import time


logger = logging.getLogger('ftw.upgrade')


class Executioner(object):

    implements(IExecutioner)
    adapts(ISetupTool)
    security = ClassSecurityInformation()

    def __init__(self, portal_setup):
        self.portal_setup = portal_setup

    security.declarePrivate('install')
    def install(self, data):
        for profileid, upgradeids in data:
            self._upgrade_profile(profileid, upgradeids)

        for adapter in self._get_sorted_post_upgrade_adapters():
            adapter()

        TransactionNote().set_transaction_note()

    security.declarePrivate('install_upgrades_by_api_ids')
    def install_upgrades_by_api_ids(self, *upgrade_api_ids):
        gatherer = IUpgradeInformationGatherer(self.portal_setup)
        upgrades = gatherer.get_upgrades_by_api_ids(*upgrade_api_ids)
        data = [(upgrade['profile'], [upgrade['id']]) for upgrade in upgrades]
        return self.install(data)

    security.declarePrivate('_upgrade_profile')
    def _upgrade_profile(self, profileid, upgradeids):
        last_dest_version = None

        for upgradeid in upgradeids:
            last_dest_version = self._do_upgrade(profileid, upgradeid) \
                or last_dest_version

        self.portal_setup.setLastVersionForProfile(
            profileid, last_dest_version)

    security.declarePrivate('_do_upgrade')
    def _do_upgrade(self, profileid, upgradeid):
        start = time.time()

        step = _upgrade_registry.getUpgradeStep(profileid, upgradeid)
        logger.log(logging.INFO, '_' * 70)
        logger.log(logging.INFO, 'UPGRADE STEP %s: %s' % (
                profileid, step.title))

        step.doStep(self.portal_setup)
        TransactionNote().add_upgrade(profileid, step.dest, step.title)

        msg = "Ran upgrade step %s for profile %s" % (
            step.title, profileid)
        logger.log(logging.INFO, msg)

        logger.log(logging.INFO, 'Upgrade step duration: %s' % format_duration(
                time.time() - start))

        return step.dest

    security.declarePrivate('_get_sorted_post_upgrade_adapters')
    def _get_sorted_post_upgrade_adapters(self):
        """Returns a list of post upgrade adapters, sorted by
        profile dependencies.
        Assumes that the names of the adapters are profile names
        (e.g. "ftw.upgrade:default").
        """

        profile_order = get_sorted_profile_ids(self.portal_setup)

        portal_url = getToolByName(self.portal_setup, 'portal_url')
        portal = portal_url.getPortalObject()
        adapters = list(getAdapters((portal, portal.REQUEST), IPostUpgrade))

        def _sorter(a, b):
            name_a = a[0]
            name_b = b[0]

            if name_a not in profile_order and name_b not in profile_order:
                return 0

            elif name_a not in profile_order:
                return -1

            elif name_b not in profile_order:
                return 1

            else:
                return cmp(profile_order.index(name_a),
                           profile_order.index(name_b))

        adapters.sort(_sorter, reverse=True)
        return [adapter for name, adapter in adapters]
