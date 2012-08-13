from Products.GenericSetup.interfaces import ISetupTool
from Products.GenericSetup.upgrade import _upgrade_registry
from ftw.upgrade.interfaces import IExecutioner
from zope.component import adapts
from zope.interface import implements
import logging
import transaction


logger = logging.getLogger('ftw.upgrade')


class Executioner(object):

    implements(IExecutioner)
    adapts(ISetupTool)

    def __init__(self, portal_setup):
        self.portal_setup = portal_setup

    def install(self, data):
        for profileid, upgradeids in data:
            self._upgrade_profile(profileid, upgradeids)

    def _upgrade_profile(self, profileid, upgradeids):
        last_dest_version = None

        for upgradeid in upgradeids:
            last_dest_version = self._do_upgrade(profileid, upgradeid) \
                or last_dest_version

        self.portal_setup.setLastVersionForProfile(
            profileid, last_dest_version)

    def _do_upgrade(self, profileid, upgradeid):
        step = _upgrade_registry.getUpgradeStep(profileid, upgradeid)
        step.doStep(self.portal_setup)

        msg = "Ran upgrade step %s for profile %s" % (
            step.title, profileid)
        logger.log(logging.INFO, msg)

        transaction_note = '%s -> %s (%s)' % (
            step.profile, '.'.join(step.dest), step.title)
        transaction.get().note(transaction_note)

        return step.dest
