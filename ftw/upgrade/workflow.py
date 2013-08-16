from Products.CMFCore.utils import getToolByName
from ftw.upgrade import ProgressLogger
from ftw.upgrade.helpers import update_security_for
from zope.component.hooks import getSite
import logging

LOG = logging.getLogger('ftw.upgrade.WorkflowChainUpdater')


class WorkflowChainUpdater(object):

    def __init__(self, objects, review_state_mapping, update_security=True):
        self.objects = tuple(objects)
        self.review_state_mapping = review_state_mapping
        self.update_security = update_security
        self.started = False
        self.wfs_and_states_before = None

    def __enter__(self):
        assert not self.started, 'WorkflowChainUpdater was already started.'
        self._started = True

        self.wfs_and_states_before = self.get_workflows_and_states(
            self.get_objects())

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type:
            return None

        self.update_workflow_states_with_mapping()

    def get_objects(self):
        return self.objects

    def get_workflows_and_states(self, objects):
        title = 'Get workflows and review states'

        wftool = None
        result = {}
        for obj in ProgressLogger(title, objects):
            if wftool is None:
                wftool = getToolByName(obj, 'portal_workflow')

            path = '/'.join(obj.getPhysicalPath())
            workflow = self._get_workflow_id_for(obj, wftool)
            if workflow:
                review_state = wftool.getInfoFor(obj, 'review_state')
            else:
                review_state = None

            result[path] = {'workflow': workflow,
                            'review_state': review_state}

        return result

    def update_workflow_states_with_mapping(self):
        status_before_activation = self.wfs_and_states_before
        status_after_activation = self.get_workflows_and_states(
            self.get_objects())

        LOG.info('Changing workflow states of objects which were'
                 ' reset to the initial state according to mapping.')

        portal = getSite()
        wf_tool = getToolByName(portal, 'portal_workflow')

        title = 'Change workflow states'
        for path in ProgressLogger(title, status_before_activation):
            wf_before = status_before_activation[path].get('workflow')
            review_state_before = status_before_activation[path].get(
                'review_state')
            wf_after = status_after_activation[path].get('workflow')
            review_state_after = status_after_activation[path].get(
                'review_state')

            if not review_state_after:
                # Object seems not to have a workflow
                continue

            if (wf_before, review_state_before) == \
                    (wf_after, review_state_after):
                # State was not changed
                continue

            mapping = self.review_state_mapping.get((wf_before, wf_after))
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
                    'review_state': new_review_state,
                    'action': ''})

            if self.update_security:
                update_security_for(obj, reindex_security=True)
                obj.reindexObject(idxs=['review_state'])

    def _get_workflow_id_for(self, context, wftool):
        workflows = wftool.getWorkflowsFor(context)
        assert len(workflows) in (0, 1), \
            'Only one workflow per object supported. %s' % str(context)

        if len(workflows) == 0:
            return None

        else:
            return workflows[0].id
