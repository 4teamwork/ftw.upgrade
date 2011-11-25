from Products.CMFCore.CatalogTool import CatalogTool
from ftw.upgrade.interfaces import ICatalogMixin
from ftw.upgrade.mixins.catalog import CatalogMixin
from plone.mocktestcase import MockTestCase
from zope.interface.verify import verifyClass


class TestCatalogMixin(MockTestCase):

    def test_implements_interface(self):
        self.assertTrue(ICatalogMixin.implementedBy(CatalogMixin))
        verifyClass(ICatalogMixin, CatalogMixin)

    def test_add_catalog_index_with_indexing(self):
        catalog = self.mocker.mock(CatalogTool)
        self.mock_tool(catalog, 'portal_catalog')
        self.expect(catalog.addIndex('my_index', 'KeywordIndex', extra=None))

        self.replay()

        obj = CatalogMixin()
        obj.add_catalog_index('my_index', 'KeywordIndex')
        self.assertEqual(obj._get_catalog_tasks(),
                         [{'indexes': ['my_index'],
                           'query': None,
                           'metadata': True}])

    def test_add_catalog_index_without_indexing(self):
        catalog = self.mocker.mock(CatalogTool)
        self.mock_tool(catalog, 'portal_catalog')
        self.expect(catalog.addIndex('my_index', 'KeywordIndex', extra=None))

        self.replay()

        obj = CatalogMixin()
        obj.add_catalog_index('my_index', 'KeywordIndex', index=False)
        self.assertEqual(obj._get_catalog_tasks(), [])

    def test_rebuild_catalog_indexes_does_queue(self):
        obj = CatalogMixin()
        obj.rebuild_catalog_indexes(indexes=['my', 'index'],
                                    query={'portal_type': ['Foo']},
                                    metadata=False)
        obj.rebuild_catalog_indexes(indexes=['other', 'indexes'],
                                    query={'portal_type': ['Bar']},
                                    metadata=True)

        self.assertEqual(
            obj._get_catalog_tasks(),
            [{'indexes': ['my', 'index'],
              'query': {'portal_type': ['Foo']},
              'metadata': False},

             {'indexes': ['other', 'indexes'],
              'query': {'portal_type': ['Bar']},
              'metadata': True}])

    def test_query_catalog_passes_to_unrestrictedSearchResults(self):
        query = {
            'portal_type': ['Foo', 'Bar'],
            'path': '/my/site'}

        catalog = self.mocker.mock(CatalogTool)
        self.mock_tool(catalog, 'portal_catalog')
        self.expect(catalog.unrestrictedSearchResults(**query))

        self.replay()
        obj = CatalogMixin()
        obj.query_catalog(query)

    def test_finish_catalog_tasks_performs_tasks_on_catalog(self):
        foo1_brain = self.mocker.mock(count=False)
        foo1_obj = self.create_dummy()
        self.expect(foo1_brain.getObject()).result(foo1_obj)
        self.expect(foo1_brain.getRID()).result(1)

        foo2_brain = self.mocker.mock(count=False)
        foo2_obj = self.create_dummy()
        self.expect(foo2_brain.getObject()).result(foo2_obj)
        self.expect(foo2_brain.getRID()).result(2)

        bar1_brain = self.mocker.mock(count=False)
        bar1_obj = self.create_dummy()
        self.expect(bar1_brain.getObject()).result(bar1_obj)
        self.expect(bar1_brain.getRID()).result(3)

        bar2_brain = self.mocker.mock(count=False)
        bar2_obj = self.create_dummy()
        self.expect(bar2_brain.getObject()).result(bar2_obj)
        self.expect(bar2_brain.getRID()).result(4)

        query1 = {'portal_type': ['Foo']}
        query2 = {'portal_type': ['Bar']}
        indexes = ['Title', 'creator']

        obj = CatalogMixin()
        obj.rebuild_catalog_indexes(indexes, query1, metadata=True)
        obj.rebuild_catalog_indexes(indexes, query2, metadata=False)

        catalog = self.mocker.mock(CatalogTool)
        self.mock_tool(catalog, 'portal_catalog')

        with self.mocker.order():
            self.expect(catalog.unrestrictedSearchResults(**query1)).result(
                [foo1_brain, foo2_brain])

            self.expect(catalog.reindexObject(foo1_obj, indexes,
                                              update_metadata=True))
            self.expect(catalog.reindexObject(foo2_obj, indexes,
                                              update_metadata=True))

            self.expect(catalog.unrestrictedSearchResults(**query2)).result(
                [bar1_brain, bar2_brain])

            self.expect(catalog.reindexObject(bar1_obj, indexes,
                                              update_metadata=False))
            self.expect(catalog.reindexObject(bar2_obj, indexes,
                                              update_metadata=False))

        self.replay()
        obj.finish_catalog_tasks()

    def test_finish_catalog_task_does_not_do_twice_the_same(self):
        catalog = self.mocker.mock(CatalogTool)
        self.mock_tool(catalog, 'portal_catalog')

        foo_brain = self.mocker.mock(count=False)
        foo_obj = self.create_dummy()
        self.expect(foo_brain.getObject()).result(foo_obj)
        self.expect(foo_brain.getRID()).result(5)

        bar_brain = self.mocker.mock(count=False)
        bar_obj = self.create_dummy()
        self.expect(bar_brain.getObject()).result(bar_obj)
        self.expect(bar_brain.getRID()).result(6)

        query1 = {'portal_type': ['Foo']}
        query2 = {'portal_type': ['Foo', 'Bar']}

        obj = CatalogMixin()
        obj.rebuild_catalog_indexes(['Title'], query1)
        obj.rebuild_catalog_indexes(['Title', 'creator'], query2)

        with self.mocker.order():
            self.expect(catalog.unrestrictedSearchResults(**query1)).result(
                [foo_brain])

            self.expect(catalog.reindexObject(foo_obj, ['Title'],
                                              update_metadata=False))

            self.expect(catalog.unrestrictedSearchResults(**query2)).result(
                [foo_brain, bar_brain])

            self.expect(catalog.reindexObject(foo_obj, ['creator'],
                                              update_metadata=False))
            self.expect(catalog.reindexObject(bar_obj, ['Title', 'creator'],
                                              update_metadata=False))

        self.replay()
        obj.finish_catalog_tasks()

    def test_finish_catalog_tasks_with_query_catalog_in_between(self):
        catalog = self.mocker.mock(CatalogTool)
        self.mock_tool(catalog, 'portal_catalog')

        foo_brain = self.mocker.mock(count=False)
        foo_obj = self.create_dummy()
        self.expect(foo_brain.getObject()).result(foo_obj)
        self.expect(foo_brain.getRID()).result(7)

        obj = CatalogMixin()
        obj.rebuild_catalog_indexes(['Title', 'SearchableText'])

        with self.mocker.order():
            self.expect(catalog.unrestrictedSearchResults()).result(
                [foo_brain])

            self.expect(catalog.reindexObject(foo_obj, ['Title'],
                                              update_metadata=False))

            self.expect(catalog.unrestrictedSearchResults(
                    Title='Foo')).result([foo_brain])

            self.expect(catalog.unrestrictedSearchResults()).result(
                [foo_brain])

            self.expect(catalog.reindexObject(foo_obj, ['SearchableText'],
                                              update_metadata=False))

        self.replay()

        self.assertEqual(obj.query_catalog({'Title': 'Foo'}), [foo_brain])
        obj.finish_catalog_tasks()
