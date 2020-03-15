from datetime import datetime
from DateTime import DateTime
from ftw.builder import Builder
from ftw.builder import create
from ftw.builder.content import dx_content_builders_registered
from ftw.testing import freeze
from ftw.upgrade.migration import BACKUP_AND_IGNORE_UNMAPPED_FIELDS
from ftw.upgrade.migration import DISABLE_FIELD_AUTOMAPPING
from ftw.upgrade.migration import FieldsNotMappedError
from ftw.upgrade.migration import IBaseObject
from ftw.upgrade.migration import IGNORE_DEFAULT_IGNORE_FIELDS
from ftw.upgrade.migration import IGNORE_STANDARD_FIELD_MAPPING
from ftw.upgrade.migration import IGNORE_UNMAPPED_FIELDS
from ftw.upgrade.migration import InplaceMigrator
from ftw.upgrade.migration import UNMAPPED_FIELDS_BACKUP_ANN_KEY
from ftw.upgrade.tests.base import UpgradeTestCase
from operator import attrgetter
from plone.app.relationfield.behavior import IRelatedItems
from plone.app.testing import login
from plone.app.testing import SITE_OWNER_NAME
from plone.app.textfield import RichTextValue
from plone.dexterity.interfaces import IDexterityContent
from plone.portlets.interfaces import IPortletAssignmentMapping
from plone.portlets.interfaces import IPortletManager
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.interfaces.constrains import ENABLED
from Products.CMFPlone.interfaces.constrains import IConstrainTypes
from Products.CMFPlone.interfaces.constrains import ISelectableConstrainTypes
from Products.CMFPlone.utils import getFSVersionTuple
from six.moves import map
from unittest import skipIf
from zope.annotation import IAnnotations
from zope.component import getMultiAdapter
from zope.component import getUtility


def todt(date):
    if isinstance(date, DateTime):
        return todt(date.asdatetime())
    return date.replace(tzinfo=None)


@skipIf(getFSVersionTuple() > (5, ),
        'The inplace migrator migrates from Archetypes.'
        ' Plone 5 has no Archetypes objects.')
class TestInplaceMigrator(UpgradeTestCase):

    def setUp(self):
        super(TestInplaceMigrator, self).setUp()
        self.wftool = getToolByName(self.portal, 'portal_workflow')
        self.wftool.setChainForPortalTypes(
            ['Document', 'Folder'],
            'simple_publication_workflow')

    def test_migrate_archetypes_folder_to_dexterity(self):
        self.grant('Manager')

        creation_date = datetime(2015, 11, 29, 10, 45)
        modification_date = datetime(2016, 1, 2, 9, 30)
        effective_date = datetime(2016, 2, 2, 2, 30)
        expires_date = datetime(2016, 3, 3, 3, 30)

        with freeze(creation_date):
            folder = create(Builder('folder')
                            .titled(u'The Folder')
                            .having(description='The Description',
                                    excludeFromNav=True,
                                    subject='One\nTwo',
                                    effectiveDate=DateTime(effective_date),
                                    expirationDate=DateTime(expires_date))
                            .in_state('published'))

        setattr(folder, '__ac_local_roles_block__', True)
        create(Builder('user').named('Hugo', 'Boss')
               .with_roles('Reader', 'Editor', on=self.portal))  # local roles!
        create(Builder('user').named('John', 'Doe')
               .with_roles('Reader', 'Editor', on=folder))

        folder._setProperty('search_label', 'HB', 'string')

        with freeze(modification_date):
            folder.reindexObject()  # update modification date

        self.assertTrue(IBaseObject.providedBy(folder))
        self.assertFalse(IDexterityContent.providedBy(folder))
        self.assertEqual(('', 'plone', 'the-folder'), folder.getPhysicalPath())
        self.assertEqual('The Folder', folder.Title())
        self.assertEqual('The Description', folder.Description())
        self.assertEqual(True, folder.exclude_from_nav())
        self.assertEqual(('One', 'Two'), folder.Subject())
        self.assertEqual(todt(creation_date), todt(folder.created()))
        self.assertEqual(todt(modification_date), todt(folder.modified()))
        self.assertEqual(todt(effective_date), todt(folder.effective()))
        self.assertEqual(todt(expires_date), todt(folder.expires()))
        self.assertEqual('HB', folder.getProperty('search_label', None))
        self.assertEqual('published', self.review_state(folder))
        self.assertEqual((('john.doe', ('Reader', 'Editor')),
                          ('test_user_1_', ('Owner',))),
                         folder.get_local_roles())

        old_catalog_indexdata = self.get_catalog_indexdata_for(folder)

        self.install_profile('plone.app.contenttypes:default')
        InplaceMigrator('Folder').migrate_object(folder)

        folder = self.portal.get('the-folder')
        self.assertFalse(IBaseObject.providedBy(folder))
        self.assertTrue(IDexterityContent.providedBy(folder))
        self.assertEqual(('', 'plone', 'the-folder'), folder.getPhysicalPath())
        self.assertEqual('The Folder', folder.Title())
        self.assertEqual('The Description', folder.Description())
        self.assertEqual(True, folder.exclude_from_nav)
        self.assertEqual(('One', 'Two'), folder.Subject())
        self.assertEqual(todt(creation_date), todt(folder.created()))
        self.assertEqual(todt(modification_date), todt(folder.modified()))
        self.assertEqual(todt(effective_date), todt(folder.effective()))
        self.assertEqual(todt(expires_date), todt(folder.expires()))
        self.assertEqual('HB', folder.getProperty('search_label', None))
        self.assertEqual('published', self.review_state(folder))
        self.assertEqual((('john.doe', ('Reader', 'Editor')),
                          ('test_user_1_', ('Owner',))),
                         folder.get_local_roles())

        self.maxDiff = None

        new_catalog_indexdata = self.get_catalog_indexdata_for(folder)
        # In Plone 4.3.7, the SearchableText changes here.
        del old_catalog_indexdata['SearchableText']
        del new_catalog_indexdata['SearchableText']

        self.assertDictEqual(old_catalog_indexdata, new_catalog_indexdata)

    def test_migrate_dexterity_folder_to_dexterity(self):
        self.grant('Manager')
        self.install_profile('plone.app.contenttypes:default')

        creation_date = datetime(2015, 11, 29, 10, 45)
        modification_date = datetime(2016, 1, 2, 9, 30)
        effective_date = datetime(2016, 2, 2, 2, 30)
        expires_date = datetime(2016, 3, 3, 3, 30)

        with dx_content_builders_registered():
            with freeze(creation_date):
                folder = create(Builder('folder')
                                .titled(u'The Folder')
                                .having(description=u'The Description',
                                        exclude_from_nav=True,
                                        subjects=(u'One', u'Two'),
                                        effective=effective_date,
                                        expires=expires_date)
                                .in_state('pending'))

        with freeze(modification_date):
            folder.reindexObject()  # update modification date

        self.assertFalse(IBaseObject.providedBy(folder))
        self.assertTrue(IDexterityContent.providedBy(folder))
        self.assertEqual(('', 'plone', 'the-folder'), folder.getPhysicalPath())
        self.assertEqual('The Folder', folder.Title())
        self.assertEqual('The Description', folder.Description())
        self.assertEqual(True, folder.exclude_from_nav)
        self.assertEqual(('One', 'Two'), folder.Subject())
        self.assertEqual(todt(creation_date), todt(folder.created()))
        self.assertEqual(todt(modification_date), todt(folder.modified()))
        self.assertEqual(todt(effective_date), todt(folder.effective()))
        self.assertEqual(todt(expires_date), todt(folder.expires()))
        self.assertEqual('pending', self.review_state(folder))

        old_catalog_indexdata = self.get_catalog_indexdata_for(folder)

        InplaceMigrator('Folder').migrate_object(folder)

        folder = self.portal.get('the-folder')
        self.assertFalse(IBaseObject.providedBy(folder))
        self.assertTrue(IDexterityContent.providedBy(folder))
        self.assertEqual(('', 'plone', 'the-folder'), folder.getPhysicalPath())
        self.assertEqual('The Folder', folder.Title())
        self.assertEqual('The Description', folder.Description())
        self.assertEqual(True, folder.exclude_from_nav)
        self.assertEqual(('One', 'Two'), folder.Subject())
        self.assertEqual(todt(creation_date), todt(folder.created()))
        self.assertEqual(todt(modification_date), todt(folder.modified()))
        self.assertEqual(todt(effective_date), todt(folder.effective()))
        self.assertEqual(todt(expires_date), todt(folder.expires()))
        self.assertEqual('pending', self.review_state(folder))

        self.maxDiff = None
        self.assertDictEqual(old_catalog_indexdata,
                             self.get_catalog_indexdata_for(folder))

    def test_migrate_archetypes_page_to_dexterity(self):
        self.grant('Manager')

        page = create(Builder('page')
                      .titled(u'The Page')
                      .having(text='<p>Some Text</p>')
                      .in_state('published'))

        self.assertTrue(IBaseObject.providedBy(page))
        self.assertFalse(IDexterityContent.providedBy(page))
        self.assertEqual('The Page', page.Title())
        self.assertEqual('<p>Some Text</p>', page.getText())
        self.assertEqual('published', self.review_state(page))

        self.install_profile('plone.app.contenttypes:default')
        InplaceMigrator('Document').migrate_object(page)

        page = self.portal.get('the-page')
        self.assertFalse(IBaseObject.providedBy(page))
        self.assertTrue(IDexterityContent.providedBy(page))
        self.assertEqual(('', 'plone', 'the-page'), page.getPhysicalPath())
        self.assertEqual('The Page', page.Title())
        self.assertIsInstance(page.text, RichTextValue)
        self.assertEqual('<p>Some Text</p>', page.text.output)
        self.assertEqual('published', self.review_state(page))

    def test_migrate_empty_richtextfield_to_dexterity(self):
        self.grant('Manager')

        no_text_page = create(Builder('page')
                              .titled(u'No Text Page')
                              .having(text=u'')
                              .in_state('published'))

        self.assertFalse(IDexterityContent.providedBy(no_text_page))
        self.assertTrue(IBaseObject.providedBy(no_text_page))
        self.assertEqual(u'', no_text_page.getText())

        self.install_profile('plone.app.contenttypes:default')
        InplaceMigrator('Document').migrate_object(no_text_page)

        no_text_page = self.portal.get('no-text-page')
        self.assertFalse(IBaseObject.providedBy(no_text_page))
        self.assertTrue(IDexterityContent.providedBy(no_text_page))
        self.assertNotIsInstance(no_text_page.text, RichTextValue)

    def test_migrate_archetypes_file_to_dexterity(self):
        self.grant('Manager')

        thefile = create(
            Builder('file')
            .titled(u'The File')
            .attach_file_containing('<doc>Content</doc>', name='data.xml'))

        self.assertTrue(IBaseObject.providedBy(thefile))
        self.assertFalse(IDexterityContent.providedBy(thefile))
        self.assertEqual('The File', thefile.Title())

        self.install_profile('plone.app.contenttypes:default')
        InplaceMigrator('File').migrate_object(thefile)

        thefile = self.portal.get('the-file')
        self.assertFalse(IBaseObject.providedBy(thefile))
        self.assertTrue(IDexterityContent.providedBy(thefile))
        self.assertEqual(('', 'plone', 'the-file'), thefile.getPhysicalPath())
        self.assertEqual('The File', thefile.Title())
        self.assertEqual('data.xml', thefile.file.filename)
        self.assertEqual('<doc>Content</doc>', thefile.file.data)

    def test_field_mapping_overrides_auto_mapping(self):
        self.grant('Manager')
        folder = create(Builder('folder').titled(u'The Title'))
        self.install_profile('plone.app.contenttypes:default')

        InplaceMigrator('Folder', {'title': 'description'},
                        ignore_fields=['description']).migrate_object(folder)
        folder = self.portal.get(folder.getId())
        self.assertEqual(u'The Title', folder.Description())

    def test_DISABLE_FIELD_AUTOMAPPING_flag(self):
        """When disabling field automapping we expect unmaped fields.
        """

        self.grant('Manager')
        folder = create(Builder('folder'))
        self.install_profile('plone.app.contenttypes:default')

        with self.assertRaises(FieldsNotMappedError) as cm:
            (InplaceMigrator('Folder', options=DISABLE_FIELD_AUTOMAPPING)
             .migrate_object(folder))

        self.assertIn('title', cm.exception.not_mapped_fields)

    def test_IGNORE_UNMAPPED_FIELDS_flag(self):
        self.grant('Manager')
        folder = create(Builder('folder'))
        self.install_profile('plone.app.contenttypes:default')

        (InplaceMigrator(
            'Folder',
            options=DISABLE_FIELD_AUTOMAPPING | IGNORE_UNMAPPED_FIELDS)
         .migrate_object(folder))

    def test_BACKUP_AND_IGNORE_UNMAPPED_FIELDS_flag(self):
        self.grant('Manager')
        folder = create(Builder('folder')
                        .titled(u'The Folder')
                        .having(description='A very fancy folder.'))
        self.install_profile('plone.app.contenttypes:default')

        new_folder = (
            InplaceMigrator(
                'Folder',
                options=DISABLE_FIELD_AUTOMAPPING | BACKUP_AND_IGNORE_UNMAPPED_FIELDS)
            .migrate_object(folder))

        self.assertEqual(
            {'nextPreviousEnabled': False,
             'description': u'A very fancy folder.',
             'contributors': (),
             'title': u'The Folder',
             'rights': u'',
             'language': u'en',
             'relatedItems': [],
             'creators': (u'test_user_1_',)},
            IAnnotations(new_folder).get(
                UNMAPPED_FIELDS_BACKUP_ANN_KEY, None))

    def test_IGNORE_STANDARD_FIELD_MAPPING_flag(self):
        self.grant('Manager')
        folder = create(Builder('folder'))
        self.install_profile('plone.app.contenttypes:default')

        with self.assertRaises(FieldsNotMappedError) as cm:
            (InplaceMigrator('Folder',
                             options=IGNORE_STANDARD_FIELD_MAPPING)
             .migrate_object(folder))

        self.assertIn('expirationDate', cm.exception.not_mapped_fields)

    def test_IGNORE_DEFAULT_IGNORE_FIELDS_flag(self):
        self.grant('Manager')
        folder = create(Builder('folder'))
        self.install_profile('plone.app.contenttypes:default')

        with self.assertRaises(FieldsNotMappedError) as cm:
            (InplaceMigrator('Folder',
                             options=IGNORE_DEFAULT_IGNORE_FIELDS)
             .migrate_object(folder))

        self.assertIn('location', cm.exception.not_mapped_fields)

    def test_migrate_constrain_types(self):
        self.grant('Manager')
        self.maxDiff = None

        folder = create(Builder('folder').titled(u'The Folder'))
        self.set_constraintypes_config(
            folder,
            {'mode': ENABLED,
             'locally allowed': ['Folder', 'Document', 'File'],
             'immediately addable': ['Folder', 'Document']})

        self.assertTrue(IBaseObject.providedBy(folder))
        self.assertFalse(IDexterityContent.providedBy(folder))
        self.assertDictEqual(
            {'mode': ENABLED,
             'locally allowed': {'Folder', 'Document', 'File'},
             'immediately addable': {'Folder', 'Document'}},
            self.get_constraintypes_config(folder))

        self.install_profile('plone.app.contenttypes:default')
        InplaceMigrator('Folder').migrate_object(folder)

        folder = self.portal.get('the-folder')
        self.assertFalse(IBaseObject.providedBy(folder))
        self.assertTrue(IDexterityContent.providedBy(folder))
        self.assertDictEqual(
            {'mode': ENABLED,
             'locally allowed': {'Folder', 'Document', 'File'},
             'immediately addable': {'Folder', 'Document'}},
            self.get_constraintypes_config(folder))

    def test_migrate_ownership(self):
        john = create(Builder('user').named('John', 'Doe').with_roles('Manager'))
        peter = create(Builder('user').named('Peter', 'Pan').with_roles('Manager'))

        login(self.portal, john.getId())
        folder = create(Builder('folder').titled(u'The Folder'))
        folder.changeOwnership(peter.getUser())

        self.assertTrue(IBaseObject.providedBy(folder))
        self.assertEqual('john.doe', folder.Creator())
        self.assertEqual('peter.pan', folder.getOwner().getId())

        self.grant('Manager')
        self.install_profile('plone.app.contenttypes:default')
        with self.login(SITE_OWNER_NAME):
            InplaceMigrator('Folder').migrate_object(folder)

        folder = self.portal.get('the-folder')
        self.assertTrue(IDexterityContent.providedBy(folder))
        self.assertEqual('john.doe', folder.Creator())
        self.assertEqual('peter.pan', folder.getOwner().getId())

    def test_migrate_ownership_no_IOwner(self):
        john = create(Builder('user').named('John', 'Doe').with_roles('Manager'))
        peter = create(Builder('user').named('Peter', 'Pan').with_roles('Manager'))

        login(self.portal, john.getId())
        folder = create(Builder('folder').titled(u'The Folder'))
        folder.changeOwnership(peter.getUser())

        self.assertTrue(IBaseObject.providedBy(folder))
        self.assertEqual('john.doe', folder.Creator())
        self.assertEqual('peter.pan', folder.getOwner().getId())

        self.grant('Manager')
        self.install_profile('plone.app.contenttypes:default')

        # The creators list behaves differently when the dublin core
        # behavior is used.
        self.portal.portal_types['Folder'].behaviors = tuple(
            name for name in self.portal.portal_types['Folder'].behaviors
            if not (name == 'plone.dublincore' or 'IDublinCore' in name
                    or name == 'plone.ownership'or 'IOwnership' in name))
        with self.login(SITE_OWNER_NAME):
            InplaceMigrator('Folder', options=IGNORE_UNMAPPED_FIELDS).migrate_object(folder)

        folder = self.portal.get('the-folder')
        self.assertTrue(IDexterityContent.providedBy(folder))
        self.assertEqual('john.doe', folder.Creator())
        self.assertEqual('peter.pan', folder.getOwner().getId())

    def test_migrate_object_position(self):
        self.grant('Manager')
        container = create(Builder('folder').titled(u'Container'))
        one = create(Builder('folder').titled(u'One').within(container))
        two = create(Builder('folder').titled(u'Two').within(container))
        three = create(Builder('folder').titled(u'Three').within(container))

        self.assertEqual(
            [0, 1, 2],
            list(map(container.getObjectPosition, ('one', 'two', 'three'))))
        container.moveObjectsByDelta(['three'], -1)
        self.assertEqual(
            [0, 2, 1],
            list(map(container.getObjectPosition, ('one', 'two', 'three'))))

        self.install_profile('plone.app.contenttypes:default')
        InplaceMigrator('Folder').migrate_object(container)
        InplaceMigrator('Folder').migrate_object(three)
        InplaceMigrator('Folder').migrate_object(two)
        InplaceMigrator('Folder').migrate_object(one)
        container = self.portal.get('container')

        self.assertEqual(
            [0, 2, 1],
            list(map(container.getObjectPosition, ('one', 'two', 'three'))))

    def test_migrate_portlets(self):
        self.grant('Manager')

        folder = create(Builder('folder').titled(u'The Folder'))
        portlet = create(Builder('static portlet')
                         .within(folder)
                         .in_manager('plone.rightcolumn'))

        self.assertEqual({'plone.leftcolumn': [],
                          'plone.rightcolumn': [portlet]},
                         self.get_portlets_for(folder))

        self.install_profile('plone.app.contenttypes:default')
        InplaceMigrator('Folder').migrate_object(folder)

        folder = self.portal.get('the-folder')
        self.assertEqual({'plone.leftcolumn': [],
                          'plone.rightcolumn': [portlet]},
                         self.get_portlets_for(folder))

    def test_migrate_relations(self):
        self.grant('Manager')

        foo = create(Builder('folder').titled(u'Foo'))
        bar = create(Builder('folder').titled(u'Bar')
                     .having(relatedItems=[foo]))

        self.assertEqual([foo], bar.getRelatedItems())
        self.assertEqual([bar], foo.getBackReferences())

        self.install_profile('plone.app.contenttypes:default')
        list(map(InplaceMigrator('Folder').migrate_object, (foo, bar)))

        foo = self.portal.get('foo')
        bar = self.portal.get('bar')

        self.assertEqual(
            [foo],
            list(map(attrgetter('to_object'), IRelatedItems(bar).relatedItems)))

    def get_catalog_indexdata_for(self, obj):
        catalog = getToolByName(obj, 'portal_catalog')
        uid = '/'.join(obj.getPhysicalPath())
        data = catalog.getIndexDataForUID(uid)

        # Remove some indexes in order to not assert them
        # since they must change from AT to DX in
        del data['meta_type']
        del data['object_provides']
        del data['created']
        del data['modified']
        data.pop('sync_uid', None)
        return data

    def review_state(self, obj):
        return self.wftool.getInfoFor(obj, 'review_state', None)

    def get_constraintypes_config(self, obj):
        ctypes = IConstrainTypes(obj)
        return {'mode': ctypes.getConstrainTypesMode(),
                'locally allowed': set(ctypes.getLocallyAllowedTypes()),
                'immediately addable': set(
                    ctypes.getImmediatelyAddableTypes())}

    def set_constraintypes_config(self, obj, config):
        self.assertEqual(
            {'mode', 'locally allowed', 'immediately addable'},
            set(config))

        ctypes = ISelectableConstrainTypes(obj)
        ctypes.setConstrainTypesMode(config['mode'])
        ctypes.setLocallyAllowedTypes(config['locally allowed'])
        ctypes.setImmediatelyAddableTypes(config['immediately addable'])

    def get_portlets_for(self, container):
        portlets = {}

        for manager_name in ('plone.leftcolumn', 'plone.rightcolumn'):
            manager = getUtility(
                IPortletManager,
                name=manager_name,
                context=self.portal
            )
            assignments = getMultiAdapter(
                (container, manager),
                IPortletAssignmentMapping,
                context=self.portal
            )
            portlets[manager_name] = list(assignments.values())

        return portlets
