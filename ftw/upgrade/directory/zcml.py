from ftw.upgrade.directory.scanner import Scanner
from operator import attrgetter
from Products.CMFPlone.interfaces import IMigratingPloneSiteRoot
from Products.GenericSetup.interfaces import EXTENSION
from Products.GenericSetup.registry import _profile_registry
from Products.GenericSetup.upgrade import _registerUpgradeStep
from Products.GenericSetup.upgrade import _upgrade_registry
from Products.GenericSetup.upgrade import UpgradeStep
from zope.configuration.fields import Path
from zope.interface import Interface
import zope.schema


class IUpgradeStepDirectoryDirective(Interface):

    profile = zope.schema.TextLine(
        title=u"GenericSetup profile id",
        required=True)

    directory = Path(
        title=u'Path to the upgrade steps directory',
        required=True)


def upgrade_step_directory_handler(context, profile, directory):
    dottedname = context.package.__name__
    context.action(
        discriminator=('upgrade-step:directory', profile),
        callable=upgrade_step_directory_action,
        args=(profile, dottedname, context.path(directory)))


def upgrade_step_directory_action(profile, dottedname, path):
    start_version = find_start_version(profile)
    scanner = Scanner(dottedname, path)

    _package, profilename = profile.split(':', 1)

    for upgrade_info in scanner.scan():
        step = UpgradeStep(upgrade_info['title'],
                           profile,
                           upgrade_info['source-version'] or start_version,
                           upgrade_info['target-version'],
                           '',
                           upgrade_info['callable'])
        _registerUpgradeStep(step)

        _profile_registry.registerProfile(
            name='{0}-upgrade-{1}'.format(profilename, upgrade_info['target-version']),
            title='Upgrade {0} to {1}: {2}'.format(
                profile,
                upgrade_info['target-version'],
                upgrade_info['title']),
            description='',
            path=upgrade_info['path'],
            product=dottedname,
            profile_type=EXTENSION,
            for_=IMigratingPloneSiteRoot)


def find_start_version(profile):
    upgrades = _upgrade_registry.getUpgradeStepsForProfile(profile).values()
    upgrades = sorted(upgrades, key=attrgetter('dest'))
    if len(upgrades) > 0:
        return upgrades[-1].dest
    else:
        return str(10**13)
