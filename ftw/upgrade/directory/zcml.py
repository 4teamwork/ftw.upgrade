from ftw.upgrade.directory.scanner import Scanner
from ftw.upgrade.directory.wrapper import wrap_upgrade_step
from ftw.upgrade.exceptions import UpgradeStepConfigurationError
from operator import attrgetter
from Products.CMFPlone.interfaces import IMigratingPloneSiteRoot
from Products.GenericSetup.interfaces import EXTENSION
from Products.GenericSetup.interfaces import IProfile
from Products.GenericSetup.registry import _profile_registry
from Products.GenericSetup.registry import GlobalRegistryStorage
from Products.GenericSetup.upgrade import _registerUpgradeStep
from Products.GenericSetup.upgrade import _upgrade_registry
from Products.GenericSetup.upgrade import UpgradeStep
from zope.configuration.fields import Path
from zope.configuration.fields import Tokens
from zope.interface import Interface

import os
import zope.schema


class IUpgradeStepDirectoryDirective(Interface):

    profile = zope.schema.TextLine(
        title=u"GenericSetup profile id",
        required=True)

    directory = Path(
        title=u'Path to the upgrade steps directory',
        required=True)

    soft_dependencies = Tokens(
        title=u'List of Generic Setup profile dependencies.',
        description=u'Format: "my.package:default"',
        required=False,
        value_type=zope.schema.TextLine())


def upgrade_step_directory_handler(context, profile, directory,
                                   soft_dependencies=None):
    dottedname = context.package.__name__
    package_dir = os.path.dirname(context.package.__file__)
    if package_dir != os.path.abspath(directory):
        dottedname += '.' + '.'.join(
            os.path.relpath(os.path.abspath(directory), package_dir)
            .split(os.sep))

    context.action(
        discriminator=('upgrade-step:directory', profile),
        callable=upgrade_step_directory_action,
        args=(profile, dottedname, context.path(directory),
              soft_dependencies))


def upgrade_step_directory_action(profile, dottedname, path,
                                  soft_dependencies):
    start_version = find_start_version(profile)
    scanner = Scanner(dottedname, path)

    if profile not in _profile_registry.listProfiles():
        raise UpgradeStepConfigurationError(
            'The profile "{0}" needs to be registered before registering its'
            ' upgrade step directory.'.format(profile))

    profileinfo = _profile_registry.getProfileInfo(profile)
    if profileinfo.get('version', None) is not None:
        raise UpgradeStepConfigurationError(
            'Registering an upgrades directory for "{0}" requires this profile'
            ' to not define a version in its metadata.xml.'
            ' The version is automatically set to the latest upgrade.'.format(
                profile))

    _package, profilename = profile.split(':', 1)
    last_version = ''.join(find_start_version(profile))
    for upgrade_info in scanner.scan():
        upgrade_profile_name = '{0}-upgrade-{1}'.format(
            profilename, upgrade_info['target-version'])

        upgrade_handler = wrap_upgrade_step(
            handler=upgrade_info['callable'],
            upgrade_profile='profile-{0}:{1}'.format(dottedname,
                                                     upgrade_profile_name),
            base_profile=profile,
            target_version=upgrade_info['target-version'])

        step = UpgradeStep(upgrade_info['title'],
                           profile,
                           upgrade_info['source-version'] or start_version,
                           upgrade_info['target-version'],
                           '',
                           upgrade_handler)
        _registerUpgradeStep(step)

        _profile_registry.registerProfile(
            name=upgrade_profile_name,
            title='Upgrade {0} to {1}: {2}'.format(
                profile,
                upgrade_info['target-version'],
                upgrade_info['title']),
            description='',
            path=upgrade_info['path'],
            product=dottedname,
            profile_type=EXTENSION,
            for_=IMigratingPloneSiteRoot)

        last_version = upgrade_info['target-version']

    profile = GlobalRegistryStorage(IProfile).get(profile)
    profile['version'] = last_version
    profile['ftw.upgrade:dependencies'] = soft_dependencies


def find_start_version(profile):
    upgrades = _upgrade_registry.getUpgradeStepsForProfile(profile).values()
    dests = set()

    for upgrade in upgrades:
        if isinstance(upgrade, list):
            # Those are combined upgrade steps
            # (registered with the upgradeSteps directive)
            [dests.update(partial_upgrade[1].dest) for partial_upgrade in upgrade]
        else:
            # Those are simple upgrade steps
            # (registered with the upgradeStep directive)
            dests.update(upgrade.dest)

    if dests:
        return max(dests)
    else:
        return str(10 ** 13)
