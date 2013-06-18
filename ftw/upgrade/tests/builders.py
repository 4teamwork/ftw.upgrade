from Acquisition import aq_base
from Products.CMFCore.utils import getToolByName
from zope.component.hooks import getSite
from zope.container.interfaces import INameChooser
import transaction


def create(builder):
    return builder.create()


def Builder(name):
    if name == "folder":
        return FolderBuilder(BuilderSession.instance())
    elif name == "document":
        return DocumentBuilder(BuilderSession.instance())


class BuilderSession(object):

    def __init__(self):
        self.reset()

    def reset(self):
        self.auto_commit = True

    @classmethod
    def instance(cls, *args, **kwgs):
        if not hasattr(cls, "_instance"):
            cls._instance = cls(*args, **kwgs)
        return cls._instance


class ATBuilder(object):

    def __init__(self, session):
        self.session = session
        self.container = getSite()
        self.arguments = {"checkConstraints": False}
        self.review_state = None

    def within(self, container):
        self.container = container
        return self

    def titled(self, title):
        self.arguments["title"] = title
        return self

    def having(self, **kwargs):
        self.arguments.update(kwargs)
        return self

    def in_state(self, review_state):
        self.review_state = review_state
        return self

    def create(self, processForm=True):
        self.before_create()
        obj = self.create_object()

        if self.review_state:
            wftool = getToolByName(self.container, 'portal_workflow')
            chain = wftool.getChainFor(obj)
            assert len(chain) == 1, \
                'Cannot change state of "%s" object - seems to have no' + \
                ' or too many workflows: %s' % (
                self.portal_type, chain)

            wftool.setStatusOf(chain[0], obj, {
                    'review_state': self.review_state})

            for workflow_id in chain:
                workflow = wftool.get(workflow_id)
                if hasattr(aq_base(workflow), 'updateRoleMappingsFor'):
                    workflow.updateRoleMappingsFor(obj)

        if processForm:
            obj.processForm()

        self.after_create(obj)
        return obj

    def create_object(self):
        name = self.choose_name()
        self.container.invokeFactory(
            self.portal_type, name, **self.arguments)
        return self.container.get(name)

    def choose_name(self):
        title = self.arguments.get('title', self.portal_type)
        chooser = INameChooser(self.container)
        return chooser.chooseName(title, self.container)

    def before_create(self):
        pass

    def after_create(self, obj):
        if self.session.auto_commit:
            transaction.commit()

class FolderBuilder(ATBuilder):

    portal_type = 'Folder'


class DocumentBuilder(ATBuilder):

    portal_type = 'Document'
