from Products.CMFPlone.interfaces import IMigratingPloneSiteRoot
from Products.GenericSetup.interfaces import EXTENSION
from Products.GenericSetup.zcml import registerProfile
from Products.GenericSetup.zcml import upgradeStep
from zope.configuration.fields import Path
from zope.interface import Interface
import zope.schema


class IImportProfileUpgradeStep(Interface):
    """Register an upgrade step which imports a generic setup profile
    specific to this upgrade step.
    """

    title = zope.schema.TextLine(
        title=u"Title",
        required=True)

    description = zope.schema.TextLine(
        title=u"Upgrade step description",
        required=False)

    profile = zope.schema.TextLine(
        title=u"GenericSetup profile id",
        required=True)

    source = zope.schema.ASCII(
        title=u"Source version",
        required=True)

    destination = zope.schema.ASCII(
        title=u"Destination version",
        required=True)

    directory = Path(
        title=u'Path',
        required=True)


def importProfileUpgradeStep(_context, title, profile, source, destination,
                             directory, description=None):
    profile_id = "upgrade_to_%s" % destination
    registerProfile(_context, name=profile_id, title=title,
                    description=description, directory=directory,
                    provides=EXTENSION, for_=IMigratingPloneSiteRoot)

    def handler(portal_setup):
        profileid = 'profile-%s:%s' % (_context.package.__name__, profile_id)
        portal_setup.runAllImportStepsFromProfile(profileid, purge_old=False)

    upgradeStep(_context, title=title, profile=profile, handler=handler,
                description=description, source=source, destination=destination)
