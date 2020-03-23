from DateTime import DateTime
from ftw.upgrade import ProgressLogger
from ftw.upgrade.helpers import update_security_for
from ftw.upgrade.utils import SavepointIterator
from ftw.upgrade.utils import SizedGenerator
from Products.CMFCore.utils import getToolByName
from six.moves import map
from six.moves import zip
from zope.component.hooks import getSite

import logging


LOG = logging.getLogger('ftw.upgrade.WorkflowChainUpdater')


class WorkflowChainUpdater(object):

    def __init__(self, objects, review_state_mapping, update_security=True,
                 migrate_workflow_history=True, transition_mapping=None, indexes=None):
        self.objects = tuple(objects)
        self.review_state_mapping = review_state_mapping
        self.update_security = update_security
        self.migrate_workflow_history = migrate_workflow_history
        self.transition_mapping = transition_mapping or {}
        self.indexes = list(indexes or []) + ['review_state']
        self.started = False
        self.wfs_and_states_before = None

    def __enter__(self):
        assert not self.started, 'WorkflowChainUpdater was already started.'
        self._started = True

        self.wfs_and_states_before = self.get_workflows_and_states(
            self.get_objects())

        return self

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
        origin_workflows = list(zip(*list(self.review_state_mapping.keys())))[0]

        title = 'Change workflow states'
        for path in ProgressLogger(title, status_before_activation):
            wf_before = status_before_activation[path].get('workflow')
            review_state_before = status_before_activation[path].get(
                'review_state')
            wf_after = status_after_activation[path].get('workflow')

            if wf_before not in origin_workflows:
                # This object has not a workflow which is in the
                # mapping, thus no migration is needed.
                continue

            mapping = self.review_state_mapping.get(
                (wf_before, wf_after), {})
            new_review_state = mapping.get(review_state_before)
            if not new_review_state:
                LOG.warn(
                    'Mapping not defined for old state %s when changing'
                    ' workflow from %s to %s.' % (
                        review_state_before, wf_before, wf_after))
                continue

            obj = portal.unrestrictedTraverse(path)

            if self.migrate_workflow_history:
                self._migrate_workflow_history(obj, wf_before, wf_after)
            else:
                wf_tool.setStatusOf(wf_after, obj, {
                    'review_state': new_review_state,
                    'action': 'systemupdate',
                    'actor': 'system',
                    'comments': '',
                    'time': DateTime()})

            if self.update_security:
                update_security_for(obj, reindex_security=True)
                obj.reindexObject(idxs=self.indexes)

    def _get_workflow_id_for(self, context, wftool):
        workflows = wftool.getWorkflowsFor(context)
        assert len(workflows) in (0, 1), \
            'Only one workflow per object supported. %s' % str(context)

        if len(workflows) == 0:
            return None

        else:
            return workflows[0].id

    def _migrate_workflow_history(self, context, old_wf, new_wf):
        wfhistory = getattr(context, 'workflow_history', None)
        if wfhistory is None or old_wf not in wfhistory:
            return

        def _migrate_action(entry):
            action = entry.get('action', None)
            if action:
                actionmapping = self.transition_mapping.get(
                    (old_wf, new_wf), {})
                if action in actionmapping:
                    entry['action'] = actionmapping[action]

            state = entry.get('review_state', None)
            if state:
                statemapping = self.review_state_mapping.get((old_wf, new_wf),
                                                             {})
                if state in statemapping:
                    entry['review_state'] = statemapping[state]

        def _migrate_entry(entry):
            entry = entry.copy()
            _migrate_action(entry)
            return entry

        wfhistory[new_wf] = list(map(_migrate_entry, wfhistory[old_wf]))


class WorkflowSecurityUpdater(object):

    def update(self, changed_workflows, reindex_security=True, savepoints=None):
        types = self.get_suspected_types(changed_workflows)
        objects = SavepointIterator.build(self.lookup_objects(types), savepoints)
        for obj in objects:
            if self.obj_has_workflow(obj, changed_workflows):
                update_security_for(obj, reindex_security=reindex_security)

    def lookup_objects(self, types):
        portal = getSite()
        catalog = getToolByName(portal, 'portal_catalog')

        query = {'portal_type': types}
        brains = tuple(catalog.unrestrictedSearchResults(query))

        lookup = lambda brain: portal.unrestrictedTraverse(brain.getPath())
        generator = SizedGenerator((lookup(brain) for brain in brains),
                                   len(brains))
        return ProgressLogger('Update object security', generator)

    def get_suspected_types(self, changed_workflows):
        types = []
        ttool = getToolByName(getSite(), 'portal_types')

        for fti in ttool.objectValues():
            portal_type = fti.getId()
            if self.type_workflow_is_one_of(portal_type, changed_workflows):
                types.append(portal_type)

        return types

    def type_workflow_is_one_of(self, portal_type, workflows):
        wftool = getToolByName(getSite(), 'portal_workflow')
        default_chain = wftool.getChainForPortalType(portal_type)
        if set(default_chain) & set(workflows):
            return True

        try:
            pwftool = getToolByName(getSite(), 'portal_placeful_workflow')
        except AttributeError:
            return False

        for policy in pwftool.objectValues():
            chain = policy.getChainFor(portal_type) or []
            if set(chain) & set(workflows):
                return True

        return False

    def obj_has_workflow(self, obj, workflows):
        wftool = getToolByName(getSite(), 'portal_workflow')
        obj_workflow_names = [wf.getId() for wf in wftool.getWorkflowsFor(obj)]
        return set(obj_workflow_names) & set(workflows)
