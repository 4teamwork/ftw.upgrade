from zope.component import Interface
from zope.configuration.fields import Path
import os
from ftw.upgrade.interfaces import IUpgradeManager
from zope.component import getUtility


class IRegisterUpgradesDirective(Interface):
    """Register Directory which contains Upgrades."""

    directory = Path(
        title=u"Directory",
        description=u"Directory containing the Upgrades",
        required=True
        )


def registerUpgrades(_context, directory):
    path = os.path.abspath(os.path.normpath(directory))
    manager = getUtility(IUpgradeManager)
    manager.add_upgrade_directory(path.encode('utf-8'))

