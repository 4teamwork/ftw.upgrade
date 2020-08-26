from Acquisition import aq_base
from Acquisition import aq_inner
from Acquisition import aq_parent
from DateTime import DateTime
from ftw.upgrade.helpers import update_security_for
from functools import partial
from operator import methodcaller
from persistent.mapping import PersistentMapping
from plone.app.relationfield.event import extract_relations
from plone.app.textfield import IRichText
from plone.app.textfield import IRichTextValue
from plone.app.uuid.utils import uuidToObject
from plone.dexterity.interfaces import IDexterityContent
from plone.dexterity.utils import createContent
from plone.dexterity.utils import iterSchemata
from plone.namedfile.interfaces import INamedBlobFileField
from plone.namedfile.interfaces import INamedBlobImageField
from plone.namedfile.interfaces import INamedField
from plone.uuid.interfaces import IMutableUUID
from plone.uuid.interfaces import IUUID
from Products.CMFPlone.interfaces import constrains
from Products.CMFPlone.utils import getFSVersionTuple
from six.moves import filter
from six.moves import map
from z3c.relationfield.event import _setRelation
from z3c.relationfield.interfaces import IRelation
from z3c.relationfield.relation import create_relation
from zope.annotation import IAnnotations
from zope.component import getUtility
from zope.container.contained import notifyContainerModified
from zope.event import notify
from zope.interface import Interface
from zope.intid.interfaces import IIntIds
from zope.keyreference.interfaces import IKeyReference
from zope.lifecycleevent import ObjectModifiedEvent
from zope.schema import getFieldsInOrder

import logging
import pkg_resources
import six


try:
    pkg_resources.get_distribution('Products.Archetypes')
except pkg_resources.DistributionNotFound:
    class IBaseObject(Interface):
        pass

    class IComputedField(Interface):
        pass
else:
    from Products.Archetypes.interfaces import IBaseObject
    from Products.Archetypes.interfaces import IComputedField

try:
    pkg_resources.get_distribution('plone.app.blob')
except pkg_resources.DistributionNotFound:
    class IBlobWrapper(Interface):
        pass
else:
    from plone.app.blob.interfaces import IBlobWrapper

try:
    pkg_resources.get_distribution('archetypes.referencebrowserwidget')
except pkg_resources.DistributionNotFound:
    class IATReferenceField(Interface):
        pass
else:
    from archetypes.referencebrowserwidget.interfaces import IATReferenceField


DISABLE_FIELD_AUTOMAPPING = 1
IGNORE_UNMAPPED_FIELDS = 2
BACKUP_AND_IGNORE_UNMAPPED_FIELDS = 4
IGNORE_STANDARD_FIELD_MAPPING = 8
IGNORE_DEFAULT_IGNORE_FIELDS = 16
SKIP_MODIFIED_EVENT = 32

UNMAPPED_FIELDS_BACKUP_ANN_KEY = 'ftw.upgrade.migration:fields_backup'

LOG = logging.getLogger('ftw.upgrade.migration')


DEFAULT_ATTRIBUTES_TO_COPY = (
    '__ac_local_roles__',
    '__ac_local_roles_block__',
    '__annotations__',
    '_count',
    '_mt_index',
    '_owner',
    '_tree',
    'workflow_history',
)


DUBLIN_CORE_IGNORES = (
    'allowDiscussion',
    'contributors',
    'creators',
    'nextPreviousEnabled',
    'rights',
    'language',
    'relatedItems',
)


DEFAULT_IGNORED_FIELDS = (
    # ID, creation date and modification date are set by method, not by field.
    'id',
    'creation_date',
    'modification_date',

    # Constrain types are not regular behaviors.
    'constrainTypesMode',
    'locallyAllowedTypes',
    'immediatelyAddableTypes',

    # The location field is no longer available in Dexterity.
    'location',

    # The presentation field is no longer available in Dexterity.
    'presentation',
)


DEFAULT_OMIT_INDEXES = (
    'SearchableText',  # expensive; should be calculated afterwards
)


STANDARD_FIELD_MAPPING = {
    'subject': 'subjects',
    'allowDiscussion': 'allow_discussion',
    'effectiveDate': 'effective',
    'expirationDate': 'expires',
    'excludeFromNav': 'exclude_from_nav',
    'tableContents': 'table_of_contents',
}


class IgnoreField(Exception):
    """Exception for indicating that the current field should
    be silently ignored.
    Used internally only.
    """


class FieldNotMappedError(ValueError):
    """A field was not mapped properly.
    """


class FieldsNotMappedError(ValueError):
    """A field was not mapped properly.
    """

    message_template = (
        'Some fields are not mapped correctly when migrating'
        ' from "{old_type}" to "{new_type}":\n\n'
        'Not mapped:\n- {not_mapped}\n\n'
        'Target fields:\n- {target_fields}\n\n'
    )

    def __init__(self, not_mapped, old_type, new_type, target_fields):
        if getFSVersionTuple() > (5, ):
            raise NotImplementedError(
                'The inplace migrator migrates from Archetypes.'
                ' Plone 5 has no Archetypes objects.')
        super(FieldsNotMappedError, self).__init__(
            self.message_template.format(
                not_mapped='\n- '.join(sorted(not_mapped)),
                old_type=old_type,
                new_type=new_type,
                target_fields='\n- '.join(sorted(target_fields))))
        self.not_mapped_fields = not_mapped
        self.old_type = old_type
        self.new_type = new_type
        self.target_fields = target_fields


class InplaceMigrator(object):
    """The inplace migrator allows to easily migrate object inplace
    to dexterity objects.

    It supports Archetypes and Dexterity frameworks as source but only can
    produce Dexterity objects as destination.
    """

    def __init__(self,
                 new_portal_type,
                 field_mapping=None,
                 options=0,
                 ignore_fields=(),
                 attributes_to_migrate=DEFAULT_ATTRIBUTES_TO_COPY,
                 additional_steps=(),
                 omit_indexes=DEFAULT_OMIT_INDEXES):

        self.new_portal_type = new_portal_type
        self.field_mapping = field_mapping or {}
        self.options = options
        self.attributes_to_migrate = attributes_to_migrate
        self.omit_indexes = omit_indexes

        self.ignore_fields = list(ignore_fields)
        if not (options & IGNORE_DEFAULT_IGNORE_FIELDS):
            self.ignore_fields.extend(DEFAULT_IGNORED_FIELDS)

        self.steps_before_clone = (
            self.dump_and_remove_references,
        )
        self.steps_after_clone = (
            self.migrate_intid,
            self.migrate_field_values,
            self.add_relations_to_relation_catalog,
            self.migrate_properties,
            self.migrate_constrain_types_configuration,
            self.update_creators,
        )
        self.additional_steps = additional_steps
        self.final_steps = (
            self.update_creation_date,
            self.update_security,
            self.trigger_modified_event,
            self.update_modification_date,
        )

    def migrate_object(self, old_object):
        list(map(lambda func: func(old_object),
                 self.steps_before_clone))
        new_object = self.clone_object(old_object)
        list(map(lambda func: func(old_object, new_object),
                 list(self.steps_after_clone)
                 + list(self.additional_steps)
                 + list(self.final_steps)))
        return new_object

    def dump_and_remove_references(self, old_object):
        """We can only remove the relations from the reference_catalog
        as long as we did not replace the object (clone_object()),
        because otherwise the catalog cannot lookup the object anymore.
        We need to remove references from the reference_catalog,
        because otherwise the references will stay forever.
        Usually, when having DX=>DX relations at the end, we should no
        longer have references in the (AT) reference_catalog but only
        in the zc.catalog (intid).
        """
        self.removed_field_values = {}

        if not IBaseObject.providedBy(old_object):
            return  # not AT

        for field in old_object.Schema().values():
            if not IATReferenceField.providedBy(field):
                continue

            value = field.getRaw(old_object)
            if not value:
                continue

            self.removed_field_values[field.__name__] = value
            field.set(old_object, ())  # removes references.

    def clone_object(self, old_object):
        new_object = self.construct_clone_for(old_object)
        self.migrate_id_and_uuid(old_object, new_object)
        self.migrate_attributes(old_object, new_object)
        new_object = self.replace_in_parent(old_object, new_object)
        return new_object

    def construct_clone_for(self, old_object):
        return createContent(self.new_portal_type)

    def migrate_id_and_uuid(self, old_object, new_object):
        new_object.id = old_object.id
        IMutableUUID(new_object).set(IUUID(old_object))

    def migrate_intid(self, old_object, new_object):
        if '_intids' not in dir(self):
            self._intids = getUtility(IIntIds)

        old_key = IKeyReference(old_object)
        new_key = IKeyReference(new_object)
        try:
            uid = self._intids.ids[old_key]
        except KeyError:
            # Key was missing in catalog
            uid = self._intids.register(new_object)
            LOG.info('Add previously unregistered object to IIntIds catalog %s', new_object)
        else:
            del self._intids.ids[old_key]
        finally:
            self._intids.refs[uid] = new_key
            self._intids.ids[new_key] = uid


    def migrate_attributes(self, old_object, new_object):
        old_object = aq_base(old_object)
        new_object = aq_base(new_object)

        for name in self.attributes_to_migrate:
            if hasattr(old_object, name):
                setattr(new_object, name, getattr(old_object, name))

    def replace_in_parent(self, old_object, new_object):
        parent = aq_parent(aq_inner(old_object))
        new_object = aq_base(new_object)
        position_in_parent = parent.getObjectPosition(old_object.id)

        parent._delOb(old_object.id)
        objects = [info for info in parent._objects
                   if info['id'] != new_object.id]
        objects = tuple(objects)
        objects += ({'id': new_object.id,
                     'meta_type': getattr(new_object, 'meta_type', None)},)
        parent._objects = objects
        parent._setOb(new_object.id, new_object)
        notifyContainerModified(parent)

        if hasattr(aq_base(parent), '_tree'):
            del parent._tree[new_object.id]
            parent._tree[new_object.id] = new_object

        parent.moveObjectToPosition(new_object.id, position_in_parent)

        return parent._getOb(new_object.id)

    def migrate_field_values(self, old_object, new_object):
        not_mapped = {}
        new_field_map = self.build_new_field_map(new_object)

        for old_fieldname, value in self.get_field_values(old_object):
            try:
                new_field = self.get_new_field(old_object,
                                               new_object,
                                               old_fieldname,
                                               new_field_map)

            except FieldNotMappedError:
                not_mapped[old_fieldname] = value
                continue

            except IgnoreField:
                continue

            else:
                self.set_field_value(new_object, new_field, value)

        if not_mapped and self.options & BACKUP_AND_IGNORE_UNMAPPED_FIELDS:
            annotations = IAnnotations(new_object)
            if UNMAPPED_FIELDS_BACKUP_ANN_KEY not in annotations:
                annotations[UNMAPPED_FIELDS_BACKUP_ANN_KEY] = (
                    PersistentMapping())

            annotations[UNMAPPED_FIELDS_BACKUP_ANN_KEY].update(not_mapped)

        elif not_mapped:
            raise FieldsNotMappedError(list(not_mapped.keys()),
                                       old_object.portal_type,
                                       new_object.portal_type,
                                       new_field_map)

    def get_new_field(self, old_object, new_object,
                      old_fieldname, new_field_map):
        if old_fieldname in self.field_mapping:
            new_fieldname = self.field_mapping[old_fieldname]
            if new_fieldname in new_field_map:
                return new_field_map[new_fieldname]

        if not (self.options & IGNORE_STANDARD_FIELD_MAPPING):
            if old_fieldname in STANDARD_FIELD_MAPPING:
                new_fieldname = STANDARD_FIELD_MAPPING[old_fieldname]
                if new_fieldname in new_field_map:
                    return new_field_map[new_fieldname]

        if not (self.options & DISABLE_FIELD_AUTOMAPPING):
            if old_fieldname in new_field_map:
                return new_field_map[old_fieldname]

        if self.options & IGNORE_UNMAPPED_FIELDS:
            raise IgnoreField()

        raise FieldNotMappedError()

    def get_field_values(self, old_object):
        if IBaseObject.providedBy(old_object):
            return self.get_at_field_values(old_object)
        elif IDexterityContent.providedBy(old_object):
            return self.get_dx_field_values(old_object)
        else:
            raise NotImplementedError('Only AT and DX is supported.')

    def get_at_field_values(self, old_object):
        for field in old_object.Schema().values():
            if IComputedField.providedBy(field):
                continue

            fieldname = field.__name__
            if fieldname in self.ignore_fields:
                continue

            value = self.removed_field_values.get(
                fieldname, field.getRaw(old_object))
            value = self.normalize_at_field_value(field, fieldname, value)
            yield fieldname, value

    def normalize_at_field_value(self, old_field, old_fieldname, value):
        recurse = partial(self.normalize_at_field_value,
                          old_field, old_fieldname)

        if isinstance(value, six.binary_type):
            return recurse(value.decode('utf-8'))

        if isinstance(value, list):
            return list(map(recurse, value))

        if isinstance(value, tuple):
            return tuple(map(recurse, value))

        if isinstance(value, DateTime):
            return recurse(value.asdatetime().replace(tzinfo=None))

        return value

    def get_dx_field_values(self, old_object):
        no_value_marker = object()

        for schemata in iterSchemata(old_object):
            storage = schemata(old_object)

            for fieldname, field in getFieldsInOrder(schemata):
                if fieldname in self.ignore_fields:
                    continue

                value = getattr(storage, fieldname, no_value_marker)
                if value == no_value_marker:
                    continue

                value = self.normalize_dx_field_value(field, fieldname, value)
                yield fieldname, value

    def normalize_dx_field_value(self, old_field, old_fieldname, value):
        return value

    def set_field_value(self, new_object, field, value):
        value = self.prepare_field_value(new_object, field, value)
        field.set(field.interface(new_object), value)

    def prepare_field_value(self, new_object, field, value):
        recurse = partial(self.prepare_field_value, new_object, field)

        if isinstance(value, six.binary_type):
            return recurse(value.decode('utf-8'))

        if isinstance(value, list):
            return list(map(recurse, value))

        if isinstance(value, tuple):
            return tuple(map(recurse, value))

        relation_fields = list(filter(
            IRelation.providedBy, (field, getattr(field, 'value_type', None))))
        if relation_fields and isinstance(value, six.text_type):
            target = uuidToObject(value)
            return create_relation('/'.join(target.getPhysicalPath()))

        if IRichText.providedBy(field) \
           and not IRichTextValue.providedBy(value):
            if not value:
                return None
            else:
                return recurse(field.fromUnicode(value))

        if INamedField.providedBy(field) and value is not None \
           and not isinstance(value, field._type):

            if value == '':
                return None

            if hasattr(value, 'get_size') and value.get_size() == 0:
                return None

            source_is_blobby = IBlobWrapper.providedBy(value)
            target_is_blobby = INamedBlobFileField.providedBy(field) or \
                               INamedBlobImageField.providedBy(field)

            if source_is_blobby and target_is_blobby:
                filename = value.filename
                if isinstance(filename, six.binary_type):
                    filename = filename.decode('utf-8')

                new_value = field._type(
                    data='',  # empty blob, will be replaced
                    contentType=value.content_type,
                    filename=filename)
                if not hasattr(new_value, '_blob'):
                    raise ValueError(
                        ('Unsupported file value type {!r}'
                         ', missing _blob.').format(
                             new_value.__class__))

                # Simply copy the persistent blob object (with the file system
                # pointer) to the new value so that the file is not copied.
                # We assume that the old object is trashed and can therefore
                # adopt the blob file.
                new_value._blob = value.getBlob()
                return recurse(new_value)

            else:
                filename = value.filename
                if isinstance(filename, six.binary_type):
                    filename = filename.decode('utf-8')

                data = value.data
                data = getattr(data, 'data', data)  # extract Pdata
                return recurse(field._type(
                    data=data,
                    contentType=value.content_type,
                    filename=filename))

        return value

    def build_new_field_map(self, new_object):
        fieldmap = {}

        for schemata in iterSchemata(new_object):
            for new_fieldname, field in getFieldsInOrder(schemata):
                if field.readonly:
                    continue

                fieldmap[new_fieldname] = field
                fieldmap['.'.join((field.interface.__identifier__,
                                   new_fieldname))] = field

        return fieldmap

    def add_relations_to_relation_catalog(self, old_object, new_object):
        for behavior_interface, name, relation in extract_relations(
                new_object):
            if isinstance(relation, (str, six.text_type)):
                # We probably got a UID, but we are working with intids
                # and can not do anything with it, so we skip it.
                LOG.warning('Got a invalid relation ({!r}), which is not '
                            'z3c.relationfield compatible.'.format(relation))
                continue

            _setRelation(new_object, name, relation)

    def migrate_properties(self, old_object, new_object):
        for item in old_object.propertyMap():
            key = item['id']
            if key == 'title':
                continue

            value = old_object.getProperty(key)
            if new_object.hasProperty(key):
                new_object._updateProperty(key, value)
            else:
                new_object._setProperty(key, value, item['type'])

    def migrate_constrain_types_configuration(self, old_object, new_object):
        old_ct = constrains.IConstrainTypes(old_object, None)
        if not old_ct:
            # No constrain types support on old object.
            # It might not be folderish.
            return

        old_mode = old_ct.getConstrainTypesMode()
        if old_mode == constrains.DISABLED:
            return

        new_ct = constrains.ISelectableConstrainTypes(new_object, None)
        if new_ct is None:
            return

        new_ct.setConstrainTypesMode(old_mode)

        if old_mode != constrains.ENABLED:
            return

        allowed_types = list(map(methodcaller('getId'),
                                 new_ct.getDefaultAddableTypes()))
        isallowed = allowed_types.__contains__
        new_ct.setLocallyAllowedTypes(
            list(filter(isallowed, old_ct.getLocallyAllowedTypes())))
        new_ct.setImmediatelyAddableTypes(
            list(filter(isallowed, old_ct.getImmediatelyAddableTypes())))

    def update_creators(self, old_object, new_object):
        """When the dublin core behavior is active, the creators are migrated already.
        But when the dublin core behavior is missing, we need to fix the creators list here.
        """
        if old_object.listCreators() != new_object.listCreators():
            new_object.setCreators(old_object.listCreators())

    def update_creation_date(self, old_object, new_object):
        new_object.creation_date = (
            old_object.created().asdatetime().replace(tzinfo=None))

    def update_security(self, old_object, new_object):
        update_security_for(new_object, reindex_security=False)

    def trigger_modified_event(self, old_object, new_object):
        if self.options & SKIP_MODIFIED_EVENT:
            return

        notify(ObjectModifiedEvent(new_object))

    def update_modification_date(self, old_object, new_object):
        new_object.setModificationDate(
            old_object.modified().asdatetime().replace(tzinfo=None))

        if not (self.options & SKIP_MODIFIED_EVENT):
            new_object.reindexObject(idxs=['modified'])
