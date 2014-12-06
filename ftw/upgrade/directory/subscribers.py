from ftw.upgrade.gatherer import flatten_upgrades
from ftw.upgrade.interfaces import IUpgradeStepRecorder
from operator import itemgetter
from Products.CMFCore.utils import getToolByName
from zope.component import getMultiAdapter
import re


def profile_installed(event):
    profile = re.sub('^profile-', '', event.profile_id)
    portal = getToolByName(event.tool, 'portal_url').getPortalObject()
    recorder = getMultiAdapter((portal, profile), IUpgradeStepRecorder)

    map(recorder.mark_as_installed,
        map(itemgetter('sdest'),
            flatten_upgrades(event.tool.listUpgrades(profile, show_old=True))))
