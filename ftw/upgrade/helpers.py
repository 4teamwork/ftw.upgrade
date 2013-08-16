from Acquisition import aq_base
from Products.CMFCore.utils import getToolByName


def update_security_for(obj, reindex_security=True):
    """Update the object security and reindex the security indexes in
    the catalog.
    """

    wftool = getToolByName(obj, 'portal_workflow')

    changed = False
    for permission in obj.permission_settings():
        roles_checked = [True for role in permission.get('roles', ())
                         if role.get('checked')]

        if roles_checked or not permission.get('acquire'):
            obj.manage_permission(permission['name'], roles=[],
                                  acquire=True)
            changed = True

    for workflow_id in wftool.getChainFor(obj):
        workflow = wftool.get(workflow_id)
        if not hasattr(aq_base(workflow), 'updateRoleMappingsFor'):
            continue

        if workflow.updateRoleMappingsFor(obj):
            changed = True

    if changed and reindex_security:
        obj.reindexObjectSecurity()

    return changed
