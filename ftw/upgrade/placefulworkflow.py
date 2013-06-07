from Acquisition import aq_base
from Products.CMFCore.utils import getToolByName
from ftw.upgrade import ProgressLogger
import logging


LOG = logging.getLogger('ftw.upgrade.PlacefulWorkflowPolicyActivator')


class PlacefulWorkflowPolicyActivator(object):

    def __init__(self, context):
        self.context = context

    def activate_policy(self, policy_id, review_state_mapping,
                        activate_in=True, activate_below=True,
                        update_security=True):

        wfs_and_states_before = self._get_workflows_and_states()

        self._activate_placeful_policy(policy_id,
                                       activate_in=activate_in,
                                       activate_below=activate_below)

        wfs_and_states_after = self._get_workflows_and_states()

        self._update_workflow_states_with_mapping(
            review_state_mapping=review_state_mapping,
            status_before_activation=wfs_and_states_before,
            status_after_activation=wfs_and_states_after)

        if update_security:
            self._update_object_security()

    def _get_workflows_and_states(self):
        LOG.info('Remember workflows and review states before activation')

        result = {}
        wftool = getToolByName(self.context, 'portal_workflow')

        def recurse(obj):
            path = '/'.join(obj.getPhysicalPath())
            workflow = self._get_workflow_id_for(obj, wftool=wftool)
            if workflow:
                review_state = wftool.getInfoFor(obj, 'review_state')
            else:
                review_state = None

            result[path] = {'workflow': workflow,
                            'review_state': review_state}

            for child in obj.objectValues():
                recurse(child)

        recurse(self.context)
        return result

    def _get_workflow_id_for(self, context, wftool=None):
        if wftool is None:
            wftool = getToolByName(self.context, 'portal_workflow')

        workflows = wftool.getWorkflowsFor(context)
        assert len(workflows) in (0, 1), \
            'Only one workflow per object supported. %s' % str(context)

        if len(workflows) == 0:
            return None

        else:
            return workflows[0].id

    def _activate_placeful_policy(self, policy_id,
                                  activate_in=True, activate_below=True):
        LOG.info('Activating placeful policy %s' % policy_id)
        pwf_tool = getToolByName(self.context, 'portal_placeful_workflow')
        policy_config = pwf_tool.getWorkflowPolicyConfig(self.context)

        if not policy_config:
            self.context.manage_addProduct[
                'CMFPlacefulWorkflow'].manage_addWorkflowPolicyConfig()
            policy_config = pwf_tool.getWorkflowPolicyConfig(self.context)


        if activate_in:
            policy_config.setPolicyIn(policy_id, update_security=False)

        if activate_below:
            policy_config.setPolicyBelow(policy_id, update_security=False)

    def _update_workflow_states_with_mapping(self,
                                             review_state_mapping,
                                             status_before_activation,
                                             status_after_activation):
        LOG.info('Changing workflow states of objects which were'
                 ' reset to the initial state according to mapping.')

        wf_tool = getToolByName(self.context, 'portal_workflow')
        portal = getToolByName(self.context, 'portal_url').getPortalObject()

        title = 'Change workflow states'
        with ProgressLogger(title, status_after_activation) as step:
            for path in status_before_activation:
                wf_before = status_before_activation[path].get('workflow')
                review_state_before = status_before_activation[path].get(
                    'review_state')
                wf_after = status_after_activation[path].get('workflow')
                review_state_after = status_after_activation[path].get(
                    'review_state')

                if not review_state_after:
                    # Object seems not to have a workflow
                    step()
                    continue

                if (wf_before, review_state_before) == \
                        (wf_after, review_state_after):
                    # State was not changed
                    step()
                    continue

                mapping = review_state_mapping.get((wf_before, wf_after))
                assert mapping, \
                    'No mapping for changing workflow "%s" to "%s"' % (
                    wf_before, wf_after)

                new_review_state = mapping.get(review_state_before)
                assert new_review_state, \
                    'Mapping not defined for old state %s when changing' +\
                    ' workflow from %s to %s.' % (
                    review_state_before, wf_before, wf_after)

                obj = portal.unrestrictedTraverse(path)
                wf_tool.setStatusOf(wf_after, obj, {
                        'review_state': new_review_state})
                step()

    def _update_object_security(self):
        wftool = getToolByName(self.context, 'portal_workflow')

        workflows = dict(filter(
                lambda item: hasattr(aq_base(item[1]),
                                     'updateRoleMappingsFor'),
                wftool.objectItems()))

        LOG.info('Updating object security...')
        count = wftool._recursiveUpdateRoleMappings(self.context, workflows)
        LOG.info('.. updated %s objects' % count)
