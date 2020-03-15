from Acquisition import aq_inner
from Acquisition import aq_parent
from datetime import datetime
from DateTime import DateTime
from ftw.builder import Builder
from ftw.builder import create
from ftw.upgrade import UpgradeStep
from ftw.upgrade.exceptions import NoAssociatedProfileError
from ftw.upgrade.indexing import HAS_INDEXING
from ftw.upgrade.indexing import processQueue
from ftw.upgrade.interfaces import IDuringUpgrade
from ftw.upgrade.interfaces import IUpgradeStep
from ftw.upgrade.tests.base import UpgradeTestCase
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.browserlayer.utils import register_layer
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.utils import getFSVersionTuple
from unittest import skipIf
from zope.interface import alsoProvides
from zope.interface import Interface
from zope.interface.verify import verifyClass

import pkg_resources

try:
    from Products.CMFPlone.utils import get_installer
except ImportError:
    get_installer = None

ALLOWED_ROLES_AND_USERS_PERMISSION = 'View'
if getFSVersionTuple() > (5, 2):
    ALLOWED_ROLES_AND_USERS_PERMISSION = 'Access contents information'


class IMyProductLayer(Interface):
    """Dummy class used in test_remove_broken_browserlayer()
    """


class TestUpgradeStep(UpgradeTestCase):

    def setUp(self):
        super(TestUpgradeStep, self).setUp()
        self.portal = self.layer['portal']
        self.portal_setup = getToolByName(self.portal, 'portal_setup')
        self.setup_logging()

        setRoles(self.portal, TEST_USER_ID, ['Manager'])

    def test_implements_interface(self):
        verifyClass(IUpgradeStep, UpgradeStep)

    def test_upgrade_classmethod(self):
        with self.assertRaises(NotImplementedError):
            UpgradeStep(self.portal_setup)

    def test_portal_setup_attribute(self):
        testcase = self

        class Step(UpgradeStep):
            def __call__(self):
                testcase.assertEqual(testcase.portal_setup, self.portal_setup)

        Step(self.portal_setup)

    def test_portal_attribute(self):
        testcase = self

        class Step(UpgradeStep):
            def __call__(self):
                testcase.assertEqual(testcase.portal, self.portal)

        Step(self.portal_setup)

    def test_getToolByName(self):
        actions_tool = getToolByName(self.portal, 'portal_actions')
        testcase = self

        class Step(UpgradeStep):
            def __call__(self):
                testcase.assertEqual(
                    actions_tool,
                    self.getToolByName('portal_actions'))

        Step(self.portal_setup)

    def test_objects_method_yields_objects_with_logging(self):
        testcase = self
        create(Builder('folder').titled(u'Foo'))
        create(Builder('folder').titled(u'Bar'))
        create(Builder('folder').titled(u'Baz'))

        object_titles = []

        class Step(UpgradeStep):
            def __call__(self):
                for obj in self.objects({'portal_type': 'Folder'},
                                        'Log message',
                                        logger=testcase.logger,
                                        savepoints=False):
                    object_titles.append(obj.Title())

        Step(self.portal_setup)

        self.assertEqual(set(['Foo', 'Bar', 'Baz']), set(object_titles))

        self.assertEqual(['STARTING Log message',
                          '1 of 3 (33%): Log message',
                          'DONE Log message'],
                         self.get_log())

    def test_objects_modifying_catalog_does_not_reduce_result_set(self):
        old_date = DateTime(2010, 1, 1)
        new_date = DateTime(2012, 3, 3)
        create(Builder('folder').with_modification_date(old_date))
        create(Builder('folder').with_modification_date(old_date))
        create(Builder('folder').with_modification_date(old_date))
        create(Builder('folder').with_modification_date(old_date))

        data = {'processed_folders': 0}

        class Step(UpgradeStep):
            def __call__(self):
                for obj in self.objects({'modified': old_date}, ''):
                    obj.setModificationDate(new_date)
                    obj.reindexObject(idxs=['modified'])
                    data['processed_folders'] += 1

        Step(self.portal_setup)
        self.assertEqual(
            4, data['processed_folders'],
            'Updating catalog reduced result set while iterating over it!!!')

    @skipIf(not HAS_INDEXING,
            'Tests must only run when indexing is available')
    def test_logs_indexing_progress(self):
        folders = [
            create(Builder('folder')),
            create(Builder('folder')),
            create(Builder('folder')),
        ]

        class Step(UpgradeStep):
            def __call__(self):
                for folder in folders:
                    folder.reindexObject()
                # manually trigger processing reindex queue
                processQueue()

        alsoProvides(self.portal.REQUEST, IDuringUpgrade)
        Step(self.portal_setup)

        self.assertEqual(['1 of 3 (33%): Processing indexing queue'],
                         self.get_log())

    def test_catalog_rebuild_index(self):
        testcase = self

        class Step(UpgradeStep):
            def __call__(self):
                ctool = self.getToolByName('portal_catalog')
                name = 'modified'
                testcase.assertEqual(1, ctool._catalog.getIndex(name).indexSize())
                self.catalog_remove_index(name)

                self.catalog_add_index(name, 'DateIndex')
                testcase.assertEqual(0, ctool._catalog.getIndex(name).indexSize())
                self.catalog_rebuild_index(name)
                testcase.assertEqual(1, ctool._catalog.getIndex(name).indexSize())

        create(Builder('folder')
               .titled(u'Rebuild Index Test Obj'))

        Step(self.portal_setup)

    def test_catalog_reindex_objects(self):
        testcase = self
        create(Builder('folder'))

        class Step(UpgradeStep):
            def __call__(self):
                ctool = self.getToolByName('portal_catalog')
                name = 'modified'
                testcase.assertEqual(1, ctool._catalog.getIndex(name).indexSize())
                self.catalog_remove_index(name)

                self.catalog_add_index(name, 'DateIndex')
                testcase.assertEqual(0, ctool._catalog.getIndex(name).indexSize())

                self.catalog_reindex_objects({'portal_type': 'Folder'})

                self.catalog_rebuild_index(name)
                testcase.assertEqual(1, ctool._catalog.getIndex(name).indexSize())

        Step(self.portal_setup)

    def test_catalog_reindex_objects_keeps_modification_date(self):
        testcase = self
        folder = create(Builder('folder'))

        modification_date = DateTime('2010/12/31')
        folder.setModificationDate(modification_date)
        folder.reindexObject(idxs=['modified'])

        class Step(UpgradeStep):
            def __call__(self):

                brain = self.catalog_unrestricted_search(
                    {'UID': folder.UID()})[0]
                testcase.assertEqual(modification_date, brain.modified)

                self.catalog_reindex_objects({})

                brain = self.catalog_unrestricted_search(
                    {'UID': folder.UID()})[0]
                testcase.assertEqual(modification_date, brain.modified)

        Step(self.portal_setup)

    def test_catalog_has_index(self):
        testcase = self

        class Step(UpgradeStep):
            def __call__(self):
                testcase.assertTrue(self.catalog_has_index('sortable_title'))
                testcase.assertFalse(self.catalog_has_index('foo'))

        Step(self.portal_setup)

    def test_catalog_add_and_remove_indexes(self):
        testcase = self

        class Step(UpgradeStep):
            def __call__(self):
                testcase.assertFalse(self.catalog_has_index('foo'))
                self.catalog_add_index('foo', 'FieldIndex')
                testcase.assertTrue(self.catalog_has_index('foo'))
                self.catalog_remove_index('foo')
                testcase.assertFalse(self.catalog_has_index('foo'))

        Step(self.portal_setup)

    def test_catalog_unrestricted_get_object(self):
        testcase = self
        folder = create(Builder('folder'))
        create(Builder('document').within(folder))

        folder_path = '/'.join(folder.getPhysicalPath())

        class Step(UpgradeStep):
            def __call__(self):
                query = {'path': folder_path,
                         'portal_type': 'Document'}
                brains = self.catalog_unrestricted_search(query)

                brain = brains[0]
                testcase.assertEqual(
                    'ImplicitAcquisitionWrapper',
                    type(brain).__name__)

                obj = self.catalog_unrestricted_get_object(brain)
                testcase.assertEqual(
                    'ImplicitAcquisitionWrapper',
                    type(obj).__name__)

        Step(self.portal_setup)

    def test_catalog_unrestricted_get_object_removes_dead_brains(self):
        """From time to time there are brains in the catalog for which the
        object no longer exists.
        This can happen because of bugs such as when a "deleted"-event-subscriber
        indexes the object.

        The ``catalog_unrestricted_get_object``, which is used internally for
        methods such as ``objects``, should therefore take care and remove those
        dead brains and log a warning while returning ``None``.
        """
        testcase = self
        folder = create(Builder('folder'))
        # Delete folder and suppress events so that the catalog does not notice
        # the object is gone, then try to get the object.
        aq_parent(aq_inner(folder))._delObject(folder.getId(),
                                               suppress_events=True)

        class Step(UpgradeStep):

            def __call__(self):
                brains = self.get_folder_brains()
                testcase.assertEqual(1, len(brains))
                brain ,= brains

                testcase.assertIsNone(
                    self.catalog_unrestricted_get_object(brain),
                    'Should return None in order to work well with .objects()')

                testcase.assertIn(
                    "The object of the brain with rid {!r} no longer exists"
                    " at the path '/plone/folder'; removing the brain.".format(
                        brain.getRID()),
                    testcase.get_log())

                testcase.assertEqual(
                    0, len(self.get_folder_brains()),
                    'Brain should have been uncataloged at this point.')

            def get_folder_brains(self):
                return self.catalog_unrestricted_search({'portal_type': 'Folder'})

        Step(self.portal_setup)

    def test_catalog_unrestricted_search(self):
        testcase = self

        folder = create(Builder('folder'))
        create(Builder('document').titled(u'Page One').within(folder))
        create(Builder('document').titled(u'Page Two').within(folder))

        folder_path = '/'.join(folder.getPhysicalPath())

        class Step(UpgradeStep):
            def __call__(self):
                query = {'path': folder_path,
                         'portal_type': 'Document'}
                brains = self.catalog_unrestricted_search(query)

                testcase.assertEqual(2, len(brains))
                testcase.assertEqual(['page-one', 'page-two'],
                                     [brain.id for brain in brains])
                testcase.assertEqual('ImplicitAcquisitionWrapper',
                                     type(brains[0]).__name__)

                objects = self.catalog_unrestricted_search(
                    query, full_objects=True)
                testcase.assertEqual(2, len(objects))
                objects = list(objects)
                testcase.assertEqual(['page-one', 'page-two'],
                                     [obj.id for obj in objects])
                testcase.assertEqual('ImplicitAcquisitionWrapper',
                                     type(objects[0]).__name__)

        Step(self.portal_setup)

    def test_catalog_unrestricted_search_filters_nonexisting_objects(self):
        """From time to time there are brains in the catalog for which the
        object no longer exists.
        This can happen because of bugs such as when a "deleted"-event-subscriber
        indexes the object.

        The ``catalog_unrestricted_get_object`` may return with ``None`` in
        such a situation, so ``catalog_unrestricted_search`` needs to filter those
        when ``full_objects`` is set to ``True``.
        """
        testcase = self
        folder = create(Builder('folder'))
        # Delete folder and suppress events so that the catalog does not notice
        # the object is gone, then try to get the object.
        aq_parent(aq_inner(folder))._delObject(folder.getId(),
                                               suppress_events=True)

        class Step(UpgradeStep):
            def __call__(self):
                query = {'portal_type': 'Folder'}
                testcase.assertEqual(
                    1, len(self.catalog_unrestricted_search(query)))

                # Setting full_objects to true should skip missing objects..
                testcase.assertEqual(
                    (),
                    tuple(self.catalog_unrestricted_search(query, full_objects=True)))

                # .. and should have removed the broken brain.
                testcase.assertEqual(
                    (),
                    tuple(self.catalog_unrestricted_search(query)))

        Step(self.portal_setup)

    def test_actions_remove_action(self):
        atool = getToolByName(self.portal, 'portal_actions')
        self.assertIn('rss', atool.get('document_actions'))
        testcase = self

        class Step(UpgradeStep):
            def __call__(self):
                testcase.assertTrue(self.actions_remove_action(
                        'document_actions', 'rss'))
                testcase.assertFalse(self.actions_remove_action(
                        'document_actions', 'rss'))

        Step(self.portal_setup)
        self.assertNotIn('rss', atool.get('document_actions'))

    def test_actions_remove_type_action(self):
        testcase = self

        class Step(UpgradeStep):
            def event_has_action(self, actionid):
                ttool = self.getToolByName('portal_types')
                fti = ttool.get('Event')

                for action in fti._actions:
                    if action.id == actionid:
                        return True

                return False

            def __call__(self):
                testcase.assertTrue(self.event_has_action('view'))
                testcase.assertTrue(
                    self.actions_remove_type_action('Event', 'view'))
                testcase.assertFalse(self.event_has_action('view'))

        Step(self.portal_setup)

    def test_actions_add_type_action(self):
        testcase = self

        class Step(UpgradeStep):
            def get_event_action(self, actionid):
                ttool = self.getToolByName('portal_types')
                fti = ttool.get('Event')

                for action in fti._actions:
                    if action.id == actionid:
                        return action

            def get_action_ids(self):
                ttool = self.getToolByName('portal_types')
                fti = ttool.get('Event')

                return [action.id for action in fti._actions]

            def __call__(self):
                testcase.assertEqual(
                    None, self.get_event_action('additional'))
                testcase.assertNotIn(
                    'additional',
                    self.get_action_ids())

                self.actions_add_type_action(
                    'Event', 'history', action_id='additional', title='Additional',
                    action='string:#', permissions=('View', ))

                testcase.assertIn(
                    'additional',
                    self.get_action_ids())

                action = self.get_event_action('additional')
                testcase.assertEqual('Additional', action.title)
                testcase.assertEqual('string:#', action.action.text)

        Step(self.portal_setup)

    def test_set_property(self):
        testcase = self

        class Step(UpgradeStep):
            def __call__(self):
                testcase.assertFalse(self.portal.hasProperty('foo'))

                self.set_property(self.portal, 'foo', 'bar')
                testcase.assertTrue(self.portal.hasProperty('foo'))
                testcase.assertEqual('bar', self.portal.getProperty('foo'))

                self.set_property(self.portal, 'foo', 'baz')
                testcase.assertEqual('baz', self.portal.getProperty('foo'))

        Step(self.portal_setup)

    def test_add_lines_to_property(self):
        testcase = self

        class Step(UpgradeStep):
            def __call__(self):
                key = 'foo-lines'

                testcase.assertFalse(self.portal.hasProperty(key))

                self.add_lines_to_property(self.portal, key, 'foo')
                testcase.assertEqual(('foo',),
                                     self.portal.getProperty(key))

                self.add_lines_to_property(self.portal, key, ['bar'])
                testcase.assertEqual(('foo', 'bar'),
                                     self.portal.getProperty(key))

                self.add_lines_to_property(self.portal, key, 'baz')
                testcase.assertEqual(('foo', 'bar', 'baz'),
                                     self.portal.getProperty(key))

                self.set_property(self.portal, key, ('foo',))
                testcase.assertEqual(('foo',),
                                     self.portal.getProperty(key))

                self.add_lines_to_property(self.portal, key, ['bar'])
                testcase.assertEqual(('foo', 'bar'),
                                     self.portal.getProperty(key))

                self.add_lines_to_property(self.portal, key, ('baz',))
                testcase.assertEqual(('foo', 'bar', 'baz'),
                                     self.portal.getProperty(key))

                self.portal.manage_delProperties([key])
                self.add_lines_to_property(self.portal, key, ['foo', 'bar'])
                testcase.assertEqual(('foo', 'bar'),
                                     self.portal.getProperty(key))

        Step(self.portal_setup)

    def test_setup_install_profile(self):
        self.package.with_profile(
            Builder('genericsetup profile')
            .with_file('catalog.xml', self.asset('exclude-from-nav-index.xml')))

        testcase = self

        class Step(UpgradeStep):
            def __call__(self):
                testcase.assertFalse(self.catalog_has_index('excludeFromNav'))
                self.setup_install_profile('profile-the.package:default')
                testcase.assertTrue(self.catalog_has_index('excludeFromNav'))

                self.catalog_remove_index('excludeFromNav')
                testcase.assertFalse(self.catalog_has_index('excludeFromNav'))
                self.setup_install_profile('profile-the.package:default', ['catalog'])
                testcase.assertTrue(self.catalog_has_index('excludeFromNav'))

        with self.package_created():
            Step(self.portal_setup)

    @skipIf(pkg_resources.get_distribution('Products.GenericSetup').parsed_version
            < pkg_resources.parse_version('1.8'),
            'Old GenericSetup version does not support dependency_strategy option.')
    def test_setup_install_profile_does_not_reinstall_installed_profiles(self):
        # In upgrades we want to avoid accidental reinstalls of dependencies
        # when they are already installed.
        # This does only work with Products.GenericSetup>=1.8

        self.package.with_profile(
            Builder('genericsetup profile')
            .named('foo')
            .with_fs_version('1000')
            .with_file(
                'properties.xml',
                '<site><property name="foo" type="string">Foo</property></site>'))

        self.package.with_profile(
            Builder('genericsetup profile')
            .named('bar')
            .with_fs_version('1000')
            .with_dependencies('the.package:foo')
            .with_file(
                'properties.xml',
                '<site><property name="bar" type="string">Bar</property></site>'))

        testcase = self

        class Step(UpgradeStep):
            def __call__(self):
                testcase.assertEqual(None, self.portal.getProperty('bar'))
                testcase.assertEqual(None, self.portal.getProperty('foo'))

                self.setup_install_profile('profile-the.package:foo')
                testcase.assertEqual(None, self.portal.getProperty('bar'))
                testcase.assertEqual('Foo', self.portal.getProperty('foo'))

                self.portal._updateProperty('foo', 'Custom')
                testcase.assertEqual(None, self.portal.getProperty('bar'))
                testcase.assertEqual('Custom', self.portal.getProperty('foo'))

                self.setup_install_profile('profile-the.package:bar')
                testcase.assertEqual('Bar', self.portal.getProperty('bar'))
                testcase.assertEqual(
                    'Custom', self.portal.getProperty('foo'),
                    'Accidental reinstall of dependency my.package:foo'
                    ' has caused the "foo" property to be reset.')

        with self.package_created():
            Step(self.portal_setup)

    def test_ensure_profile_installed(self):
        self.package.with_profile(Builder('genericsetup profile')
                                  .with_fs_version('1111'))

        testcase = self

        class Step(UpgradeStep):
            def __call__(self):
                testcase.assertEqual('unknown', self.get_version())
                self.ensure_profile_installed('profile-the.package:default')
                testcase.assertEqual((u'1111',), self.get_version())
                self.set_version((u'1000',))
                testcase.assertEqual((u'1000',), self.get_version())
                self.ensure_profile_installed('profile-the.package:default')
                testcase.assertEqual(
                    (u'1000',), self.get_version(),
                    'Profile should not have been installed again because it'
                    ' was already installed.')

            def get_version(self):
                return self.getToolByName('portal_setup').getLastVersionForProfile(
                    'the.package:default')

            def set_version(self, version):
                return self.getToolByName('portal_setup').setLastVersionForProfile(
                    'the.package:default', version)

        with self.package_created():
            Step(self.portal_setup)

    def test_install_upgrade_profile(self):
        class AddSiteProperty(UpgradeStep):
            def __call__(self):
                assert not self.portal.getProperty('foo'), \
                    'property "foo" should not yet exist'
                self.install_upgrade_profile()
                assert self.portal.getProperty('foo') == 'bar', \
                    'property "foo" was not created or is incorrect.'

        self.package.with_profile(
            Builder('genericsetup profile')
            .with_upgrade(Builder('ftw upgrade step')
                          .to(datetime(2011, 1, 1))
                          .calling(AddSiteProperty)
                          .with_file('properties.xml', self.asset('foo-property.xml'))))

        with self.package_created():
            self.install_profile('the.package:default', '0')
            self.install_profile_upgrades('the.package:default')

    def test_install_upgrade_profile_raises_exception_when_no_profile_defined(self):
        class Step(UpgradeStep):
            def __call__(self):
                self.install_upgrade_profile()

        with self.assertRaises(NoAssociatedProfileError):
            Step(self.portal_setup)

    def test_is_product_installed(self):
        testcase = self

        class Step(UpgradeStep):
            def __call__(self):
                testcase.assertTrue(self.is_product_installed(
                    'CMFPlacefulWorkflow'))
                self.uninstall_product('CMFPlacefulWorkflow')
                testcase.assertFalse(self.is_product_installed(
                    'CMFPlacefulWorkflow'))

        Step(self.portal_setup)

    def test_is_profile_installed(self):
        self.package.with_profile(Builder('genericsetup profile')
                                  .with_fs_version('1000'))
        testcase = self

        class Step(UpgradeStep):
            def __call__(self):
                testcase.assertFalse(self.is_profile_installed(
                    'profile-the.package:default'))
                testcase.assertFalse(self.is_profile_installed(
                    'the.package:default'))
                self.setup_install_profile('profile-the.package:default')
                testcase.assertTrue(self.is_profile_installed(
                    'profile-the.package:default'))
                testcase.assertTrue(self.is_profile_installed(
                    'the.package:default'))

        with self.package_created():
            Step(self.portal_setup)

    def test_is_profile_installed_respects_quickinstaller_uninstall(self):
        testcase = self

        class Step(UpgradeStep):
            def __call__(self):
                testcase.assertFalse(self.is_profile_installed(
                    'Products.CMFPlacefulWorkflow:CMFPlacefulWorkflow'))
                self.setup_install_profile(
                    'Products.CMFPlacefulWorkflow:CMFPlacefulWorkflow')
                testcase.assertTrue(self.is_profile_installed(
                    'Products.CMFPlacefulWorkflow:CMFPlacefulWorkflow'))
                self.uninstall_product('Products.CMFPlacefulWorkflow')
                testcase.assertFalse(self.is_profile_installed(
                    'Products.CMFPlacefulWorkflow:CMFPlacefulWorkflow'))

    def test_uninstall_product(self):
        if get_installer is not None:
            quickinstaller = get_installer(self.portal, self.portal.REQUEST)
            quickinstaller.install_product('CMFPlacefulWorkflow')
            is_product_installed = quickinstaller.is_product_installed
        else:
            quickinstaller = getToolByName(self.portal, 'portal_quickinstaller')
            quickinstaller.installProduct('CMFPlacefulWorkflow')
            is_product_installed = quickinstaller.isProductInstalled

        class Step(UpgradeStep):
            def __call__(self):
                self.uninstall_product('CMFPlacefulWorkflow')

        self.assertTrue(
            is_product_installed('CMFPlacefulWorkflow'),
            'CMFPlacefulWorkflow should be installed')
        Step(self.portal_setup)
        self.assertFalse(
            is_product_installed('CMFPlacefulWorkflow'),
            'CMFPlacefulWorkflow should not be installed')

    def test_migrate_class(self):
        folder = create(Builder('folder'))
        subfolder = create(Builder('folder').within(folder))

        class FancyFolder(subfolder.__class__):
            pass

        class Step(UpgradeStep):
            def __call__(self):
                self.migrate_class(subfolder, FancyFolder)

        self.assertIn(subfolder.__class__.__name__,
                      ('ATFolder', 'Folder'))
        Step(self.portal_setup)
        self.assertEqual('FancyFolder', subfolder.__class__.__name__)

    def test_migrate_class_also_updates_provided_interfaces_info(self):
        if getFSVersionTuple() > (5, ):
            from plone.app.contenttypes.content import Link
            from plone.app.contenttypes.interfaces import ILink
            from plone.app.contenttypes.interfaces import IDocument
        else:
            from Products.ATContentTypes.content.link import ATLink as Link
            from Products.ATContentTypes.interfaces import IATLink as ILink
            from Products.ATContentTypes.interfaces import IATDocument as IDocument

        obj = create(Builder('document'))
        self.assertTrue(IDocument.providedBy(obj))
        self.assertFalse(ILink.providedBy(obj))

        class Step(UpgradeStep):
            def __call__(self):
                self.migrate_class(obj, Link)

        Step(self.portal_setup)
        self.assertFalse(IDocument.providedBy(obj),
                         'Document interface not removed in migration')
        self.assertTrue(ILink.providedBy(obj),
                        'Link interface not added in migration')

    def test_remove_broken_browserlayer(self):
        from plone.browserlayer.utils import registered_layers
        from plone.browserlayer.interfaces import ILocalBrowserLayerType
        register_layer(IMyProductLayer, 'my.product')

        class Step(UpgradeStep):
            def __call__(self):
                self.remove_broken_browserlayer('my.product',
                                                'IMyProductLayer')
        Step(self.portal_setup)

        # Check that it worked.  Note that this check fails if you have called
        # registered_layers earlier in this test before calling
        # remove_broken_browserlayer: the previous answer is cached.
        self.assertFalse(IMyProductLayer in registered_layers())
        # Check it a bit more low level.
        sm = self.portal.getSiteManager()

        adapters = sm.utilities._adapters
        self.assertFalse('my.product' in adapters[0][ILocalBrowserLayerType])
        subscribers = sm.utilities._subscribers
        layer_subscribers = subscribers[0][ILocalBrowserLayerType]
        iface_name = 'IMyProductLayer'
        self.assertEqual(len([layer for layer in layer_subscribers['']
                              if layer.__name__ == iface_name]), 0)
        self.assertNotIn((ILocalBrowserLayerType, 'my.product'),
                         sm._utility_registrations)

    def test_remove_broken_browserlayer_doesnt_fail_if_layer_missing(self):
        class Step(UpgradeStep):
            def __call__(self):
                self.remove_broken_browserlayer('my.nonexistent.product',
                                                'IMyNonexistentProductLayer')
        Step(self.portal_setup)

    def test_remove_remove_broken_portlet_manager(self):
        from plone.portlets.interfaces import IPortletManager
        from plone.portlets.interfaces import IPortletManagerRenderer
        from plone.portlets.manager import PortletManager
        from zope.browser.interfaces import IBrowserView
        from zope.publisher.interfaces.browser import IBrowserRequest

        sm = self.portal.getSiteManager()
        sm.registerUtility(component=PortletManager(),
                           provided=IPortletManager,
                           name='my.manager')

        self.assertIsNotNone(sm.adapters.lookup(
            [Interface, IBrowserRequest, IBrowserView],
            IPortletManagerRenderer,
            'my.manager'))
        self.assertIsNotNone(sm.queryUtility(
            IPortletManager, name='my.manager'))

        class Step(UpgradeStep):
            def __call__(self):
                self.remove_broken_portlet_manager('my.manager')
        Step(self.portal_setup)

        self.assertIsNone(sm.adapters.lookup(
            [Interface, IBrowserRequest, IBrowserView],
            IPortletManagerRenderer,
            'my.manager'))
        self.assertIsNone(sm.queryUtility(
            IPortletManager, name='my.manager'))


    def test_update_security_removes_roles_unmanaged_by_workflow(self):
        self.set_workflow_chain(for_type='Folder',
                                to_workflow='plone_workflow')
        folder = create(Builder('folder'))

        self.assert_permission_not_acquired('View', folder)
        self.assert_permission_not_acquired('Modify portal content', folder)
        self.assert_permission_acquired('List folder contents', folder)

        folder.manage_permission('Modify portal content', roles=[],
                                 acquire=True)
        folder.manage_permission('List folder contents', roles=[],
                                 acquire=False)

        self.assert_permission_not_acquired('View', folder)
        self.assert_permission_acquired('Modify portal content', folder)
        self.assert_permission_not_acquired('List folder contents', folder)

        class Step(UpgradeStep):
            def __call__(self):
                self.update_security(folder)
        Step(self.portal_setup)

        self.assert_permission_not_acquired('View', folder)
        self.assert_permission_not_acquired('Modify portal content', folder)
        self.assert_permission_acquired('List folder contents', folder)

    def test_update_security_reindexes_security_indexes(self):
        self.set_workflow_chain(for_type='Folder',
                                to_workflow='simple_publication_workflow')
        folder = create(Builder('folder')
                        .in_state('published'))

        self.assertEqual(['Anonymous'],
                         self.get_allowed_roles_and_users_for(folder))
        folder.reindexObjectSecurity()

        folder.manage_permission(
            ALLOWED_ROLES_AND_USERS_PERMISSION, roles=['Reader'], acquire=False)
        folder.reindexObjectSecurity()

        self.assertEqual(['Reader'],
                         self.get_allowed_roles_and_users_for(folder))

        class Step(UpgradeStep):
            def __call__(self):
                self.update_security(folder)
        Step(self.portal_setup)

        self.assertEqual(['Anonymous'],
                         self.get_allowed_roles_and_users_for(folder))

    def test_update_security_without_reindexing_security(self):
        self.set_workflow_chain(for_type='Folder',
                                to_workflow='simple_publication_workflow')
        folder = create(Builder('folder')
                        .in_state('published'))

        self.assertEqual(['Anonymous'],
                         self.get_allowed_roles_and_users_for(folder))

        folder.manage_permission(
            ALLOWED_ROLES_AND_USERS_PERMISSION, roles=['Reader'], acquire=False)
        folder.reindexObjectSecurity()

        self.assertEqual(['Reader'],
                         self.get_allowed_roles_and_users_for(folder))

        class Step(UpgradeStep):
            def __call__(self):
                self.update_security(folder, reindex_security=False)
        Step(self.portal_setup)

        self.assertEqual(['Reader'],
                         self.get_allowed_roles_and_users_for(folder))

    def test_update_workflow_security_updates_security(self):
        self.set_workflow_chain(for_type='Folder',
                                to_workflow='plone_workflow')
        folder = create(Builder('folder'))
        self.assert_permission_not_acquired('Modify portal content', folder)
        folder.manage_permission('Modify portal content', roles=[],
                                 acquire=True)
        self.assert_permission_acquired('Modify portal content', folder)

        class Step(UpgradeStep):
            def __call__(self):
                self.update_workflow_security(['plone_workflow'])
        Step(self.portal_setup)

        self.assert_permission_not_acquired('Modify portal content', folder)

    def test_update_workflow_security_reindexes_security(self):
        self.set_workflow_chain(for_type='Folder',
                                to_workflow='plone_workflow')
        folder = create(Builder('folder').in_state('published'))

        folder.manage_permission(
            ALLOWED_ROLES_AND_USERS_PERMISSION, roles=['Reader'], acquire=False)
        folder.reindexObjectSecurity()
        self.assertEqual(['Reader'],
                         self.get_allowed_roles_and_users_for(folder))

        class Step(UpgradeStep):
            def __call__(self):
                self.update_workflow_security(
                    ['plone_workflow'], reindex_security=False)
        Step(self.portal_setup)

        self.assertEqual(['Reader'],
                         self.get_allowed_roles_and_users_for(folder))

        class Step(UpgradeStep):
            def __call__(self):
                self.update_workflow_security(
                    ['plone_workflow'], reindex_security=True)
        Step(self.portal_setup)

        self.assertEqual(['Anonymous'],
                         self.get_allowed_roles_and_users_for(folder))

    def test_update_workflow_security_expects_list_of_workflows(self):
        class Step(UpgradeStep):
            def __call__(self):
                self.update_workflow_security('foo')

        with self.assertRaises(ValueError) as cm:
            Step(self.portal_setup)

        self.assertEqual('"workflows" must be a list of workflow names.',
                         str(cm.exception))

    def test_base_profile_and_target_version_are_stored_in_attribute(self):
        result = {}

        class Step(UpgradeStep):
            def __call__(self):
                result['base_profile'] = self.base_profile
                result['target_version'] = self.target_version

        Step(self.portal_setup,
             base_profile='profile-ftw.upgrade:default',
             target_version=1500)

        self.assertEqual(
            {'base_profile': 'profile-ftw.upgrade:default',
             'target_version': 1500},
            result)

    def set_workflow_chain(self, for_type, to_workflow):
        wftool = getToolByName(self.portal, 'portal_workflow')
        wftool.setChainForPortalTypes((for_type,),
                                      (to_workflow,))

    def assert_permission_acquired(self, permission, obj):
        not_acquired_permissions = self.get_not_acquired_permissions_of(obj)

        self.assertNotIn(
            permission, not_acquired_permissions,
            'Expected permission "%s" to be acquired on %s' % (
                permission, str(obj)))

    def assert_permission_not_acquired(self, permission, obj):
        not_acquired_permissions = self.get_not_acquired_permissions_of(obj)

        self.assertIn(
            permission, not_acquired_permissions,
            'Expected permission "%s" to NOT be acquired on %s' % (
                permission, str(obj)))

    def get_not_acquired_permissions_of(self, obj):
        acquired_permissions = [
            item for item in obj.permission_settings()
            if not item.get('acquire')
        ]

        return [item.get('name') for item in acquired_permissions]

    def get_allowed_roles_and_users_for(self, obj):
        processQueue()  # trigger async indexing
        catalog = getToolByName(self.portal, 'portal_catalog')
        path = '/'.join(obj.getPhysicalPath())
        rid = catalog.getrid(path)
        index_data = catalog.getIndexDataForRID(rid)
        return index_data.get('allowedRolesAndUsers')
