from contextlib import contextmanager
from ftw.upgrade.gatherer import flatten_upgrades
from ftw.upgrade.interfaces import IUpgradeStepRecorder
from functools import partial
from operator import itemgetter
from Products.CMFCore.utils import getToolByName
from six.moves import map
from zope.component import getMultiAdapter

import os
import re


DISABLE_UPGRADE_STEP_MARKING_KEY = 'ftw_upgrade_disable_upgrade_step_marking'
ALL_FLAG = 'all'


@contextmanager
def no_upgrade_step_marking(*only_profiles):
    if only_profiles:
        value = ','.join(map(partial(re.sub, '^profile-', ''), only_profiles))
    else:
        value = ALL_FLAG

    previous_value = os.environ.get(DISABLE_UPGRADE_STEP_MARKING_KEY, None)
    os.environ[DISABLE_UPGRADE_STEP_MARKING_KEY] = value

    try:
        yield
    finally:
        if previous_value:
            os.environ[DISABLE_UPGRADE_STEP_MARKING_KEY] = previous_value
        else:
            os.environ.pop(DISABLE_UPGRADE_STEP_MARKING_KEY, None)


def profile_installed(event):
    if not event.profile_id:
        return

    if not event.full_import:
        return

    disabled_for_profiles = os.environ.get(DISABLE_UPGRADE_STEP_MARKING_KEY, '').split(',')
    profile = re.sub('^profile-', '', event.profile_id)
    if profile in disabled_for_profiles or ALL_FLAG in disabled_for_profiles:
        return

    portal = getToolByName(event.tool, 'portal_url').getPortalObject()
    recorder = getMultiAdapter((portal, profile), IUpgradeStepRecorder)

    list(map(recorder.mark_as_installed, map(
        itemgetter('sdest'), flatten_upgrades(
            event.tool.listUpgrades(profile, show_old=True)))))
