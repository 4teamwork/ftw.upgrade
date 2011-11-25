from zope.component import Interface
from zope.configuration.fields import Tokens, GlobalObject
from ftw.upgrade.interfaces import IUpgradeManager
from zope.component import getUtility


class IRegisterUpgradesDirective(Interface):
    """Register Module which contains Upgrades."""

    modules = Tokens(
        title=u"Module",
        description=u"Module containing the Upgrades",
        required=True,
        value_type=GlobalObject()
        )


def registerUpgrades(_context, modules):
    manager = getUtility(IUpgradeManager)
    for module in modules:
        manager.add_upgrade_package(module)
