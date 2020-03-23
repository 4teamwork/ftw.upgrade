from zope.component import queryUtility
from zope.intid.interfaces import IIntIds


def update_intids_after_class_migration(event):
    """Update references to class-migrated objects in the intid utility.

    After a class migration all references to the migrated object need to be
    updated, see:
    https://www.fourdigits.nl/blog/changing-your-packagename#1411464714874959

    Intids KeyReferenceToPersistent instances keep references to the objects
    for which they generate an intid. These references need to be updated by
    telling containing bucket that it has changed. The easiest way to do this
    is to delete and re-add the object to the tree.
    """

    intids = queryUtility(IIntIds)
    # plone.app.intid is in the path but the profile is not installed
    if not intids:
        return

    obj = event.object
    intid = intids.queryId(obj)
    # the object does not have an intid.
    if intid is None:
        return

    reference_to_persistent = intids.refs[intid]
    # refresh buckets by deleting and re-adding objects.
    del intids.refs[intid]
    del intids.ids[reference_to_persistent]
    intids.refs[intid] = reference_to_persistent
    intids.ids[reference_to_persistent] = intid
    reference_to_persistent._p_changed = True
