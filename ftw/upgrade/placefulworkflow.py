from ftw.upgrade.workflow import WorkflowChainUpdater
from Products.CMFCore.utils import getToolByName

import logging


LOG = logging.getLogger('ftw.upgrade.PlacefulWorkflowPolicyActivator')


class PlacefulWorkflowPolicyActivator(object):

    def __init__(self, context):
        self.context = context

    def activate_policy(self, policy_id, review_state_mapping,
                        activate_in=True, activate_below=True,
                        **chain_updater_kwargs):

        with WorkflowChainUpdater(self.get_objects(), review_state_mapping,
                                  **chain_updater_kwargs):
            self._activate_placeful_policy(policy_id,
                                           activate_in=activate_in,
                                           activate_below=activate_below)

    def get_objects(self):
        objects = []

        def recurse(obj):
            objects.append(obj)
            for child in obj.objectValues():
                recurse(child)

        recurse(self.context)
        return objects

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
