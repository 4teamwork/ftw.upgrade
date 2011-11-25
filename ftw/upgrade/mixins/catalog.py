from Products.CMFCore.utils import getToolByName
from ftw.upgrade.interfaces import ICatalogMixin
from zope.app.component.hooks import getSite
from zope.interface import implements


class CatalogMixin(object):
    implements(ICatalogMixin)

    def __init__(self):
        self._catalog = None
        self._catalog_tasks = []
        self._catalog_indexed = {}  # key: rid; value: list of indexes

    def add_catalog_index(self, name, meta_type, extra=None, index=True):
        self.catalog.addIndex(name, meta_type, extra=extra)

        if index:
            self.rebuild_catalog_indexes([name], metadata=True)

    def rebuild_catalog_indexes(self, indexes, query=None, metadata=False):
        self._catalog_tasks.append({'indexes': indexes,
                                    'query': query,
                                    'metadata': metadata})

    def query_catalog(self, query):
        for task in self._catalog_tasks:
            indexes = []
            for idx in task['indexes']:
                if idx in query:
                    indexes.append(idx)
            if indexes:
                self._catalog_execute_task(indexes, task['query'],
                                           task['metadata'])

        return self.catalog.unrestrictedSearchResults(**query)

    def finish_catalog_tasks(self):
        for task in self._catalog_tasks:
            self._catalog_execute_task(**task)

    def _catalog_execute_task(self, indexes, query, metadata):
        if query:
            brains = self.catalog.unrestrictedSearchResults(**query)
        else:
            brains = self.catalog.unrestrictedSearchResults()

        for brain in brains:
            already_indexed = []
            if brain.getRID() in self._catalog_indexed:
                already_indexed = self._catalog_indexed[brain.getRID()]

            indexes_to_index = list(set(indexes) - set(already_indexed))
            self.catalog.reindexObject(brain.getObject(), indexes_to_index,
                                       update_metadata=metadata)

            if brain.getRID() not in self._catalog_indexed:
                self._catalog_indexed[brain.getRID()] = indexes_to_index
            else:
                self._catalog_indexed[brain.getRID()] += indexes_to_index

    def _get_catalog_tasks(self):
        return self._catalog_tasks

    @property
    def catalog(self):
        if getattr(self, '_catalog', None) is None:
            self._catalog = getToolByName(getSite(), 'portal_catalog')
        return self._catalog
