from AccessControl.SecurityInfo import ClassSecurityInformation
from distutils.version import LooseVersion
from ftw.upgrade.indexing import processQueue
from ftw.upgrade.interfaces import IDuringUpgrade
from ftw.upgrade.interfaces import IExecutioner
from ftw.upgrade.interfaces import IPostUpgrade
from ftw.upgrade.interfaces import IUpgradeInformationGatherer
from ftw.upgrade.resource_registries import recook_resources
from ftw.upgrade.transactionnote import TransactionNote
from ftw.upgrade.utils import format_duration
from ftw.upgrade.utils import get_sorted_profile_ids
from ftw.upgrade.utils import optimize_memory_usage
from Products.CMFCore.utils import getToolByName
from Products.GenericSetup.interfaces import ISetupTool
from Products.GenericSetup.upgrade import _upgrade_registry
from zope.component import adapts
from zope.component import getAdapters
from zope.interface import alsoProvides
from zope.interface import implementer

import logging
import time
import transaction

try:
    from Products.CMFPlone.utils import get_installer
except ImportError:
    get_installer = None


logger = logging.getLogger('ftw.upgrade')


@implementer(IExecutioner)
class Executioner(object):

    adapts(ISetupTool)
    security = ClassSecurityInformation()

    def __init__(self, portal_setup):
        self.portal_setup = portal_setup
        alsoProvides(portal_setup.REQUEST, IDuringUpgrade)

    security.declarePrivate('install')
    def install(self, data):
        self._register_after_commit_hook()
        for profileid, upgradeids in data:
            self._upgrade_profile(profileid, upgradeids)

        for adapter in self._get_sorted_post_upgrade_adapters():
            adapter()

        TransactionNote().set_transaction_note()
        recook_resources()
        self._process_indexing_queue()

    security.declarePrivate('install_upgrades_by_api_ids')
    def install_upgrades_by_api_ids(self, *upgrade_api_ids, **kwargs):
        gatherer = IUpgradeInformationGatherer(self.portal_setup)
        upgrades = gatherer.get_upgrades_by_api_ids(*upgrade_api_ids, **kwargs)
        data = [(upgrade['profile'], [upgrade['id']]) for upgrade in upgrades]
        return self.install(data)

    security.declarePrivate('install_profiles_by_profile_ids')
    def install_profiles_by_profile_ids(self, *profile_ids, **options):
        force_reinstall = options.get('force_reinstall', False)
        for profile_id in profile_ids:
            # Starting from GenericSetup 1.8.0 getLastVersionForProfile can
            # handle profile ids with or without 'profile-' prefix, but we need
            # to support older versions as well, which only support it without
            # the prefix.
            prefix = 'profile-'
            if profile_id.startswith(prefix):
                profile_id = profile_id[len(prefix):]
            installed = self.portal_setup.getLastVersionForProfile(profile_id)
            if installed != 'unknown' and not force_reinstall:
                logger.info('Ignoring already installed profile %s.',
                            profile_id)
                continue
            logger.info('Installing profile %s.', profile_id)
            # For runAllImportStepsFromProfile we still must have 'profile-' at
            # the start.
            self.portal_setup.runAllImportStepsFromProfile(prefix + profile_id)
            logger.info('Done installing profile %s.', profile_id)
            optimize_memory_usage()
        self._process_indexing_queue()

    security.declarePrivate('_register_after_commit_hook')
    def _register_after_commit_hook(self):

        def notification_hook(success, *args, **kwargs):
            result = success and 'committed' or 'aborted'
            logger.info('Transaction has been %s.' % result)

        txn = transaction.get()
        txn.addAfterCommitHook(notification_hook)

    def _process_indexing_queue(self):
        """Reindex all objects in the indexing queue.

        Process the indexing queue after installing upgrades to ensure that
        its progress is also logged to the ResponseLogger.
        """
        processQueue()

    security.declarePrivate('_upgrade_profile')
    def _upgrade_profile(self, profileid, upgradeids):
        last_dest_version = None

        for upgradeid in upgradeids:
            last_dest_version = self._do_upgrade(profileid, upgradeid) \
                or last_dest_version

        old_version = self.portal_setup.getLastVersionForProfile(profileid)
        compareable = lambda v: LooseVersion('.'.join(v))

        if old_version == 'unknown' or \
           compareable(last_dest_version) > compareable(old_version):
            self.portal_setup.setLastVersionForProfile(
                profileid, last_dest_version)

        self._set_quickinstaller_version(profileid)

    security.declarePrivate('_set_quickinstaller_version')
    def _set_quickinstaller_version(self, profileid):
        try:
            profileinfo = self.portal_setup.getProfileInfo(profileid)
        except KeyError:
            return
        product = profileinfo['product']

        if get_installer is None:
            quickinstaller = getToolByName(self.portal_setup,
                                           'portal_quickinstaller')
            if not quickinstaller.isProductInstalled(product):
                return

            version = quickinstaller.getProductVersion(product)
            if version:
                quickinstaller.get(product).installedversion = version

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

        def sort_key(item):
            name = item[0]
            if name not in profile_order:
                return -1
            else:
                return profile_order.index(name)

        adapters.sort(key=sort_key)
        return [adapter for name, adapter in adapters]
