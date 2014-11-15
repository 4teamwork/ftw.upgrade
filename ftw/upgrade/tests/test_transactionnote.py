from ftw.upgrade.transactionnote import TransactionNote
from unittest2 import TestCase
import transaction



class TestTransactionNote(TestCase):

    def setUp(self):
        transaction.begin()

    def tearDown(self):
        self.assertLess(len(transaction.get().description), 65533,
                        'Transaction note should never be longer than 65533')
        transaction.abort()

    def test_transaction_note_is_updated(self):
        note = TransactionNote()
        note.add_upgrade('my.package:default', ('1','1'), 'Migrate objects')
        note.add_upgrade('my.package:default', ('1702',), 'Remove utility')
        note.set_transaction_note()

        self.assertEquals(
            u'my.package:default -> 1.1 (Migrate objects)\n'
            u'my.package:default -> 1702 (Remove utility)',
            transaction.get().description)

    def test_description_is_removed_when_note_gets_too_long(self):
        # Transaction note size is limited to 65533 characters
        description = 'A' * (65533 / 2)

        note = TransactionNote()
        note.add_upgrade('my.package:default', ('1000',), description)
        note.add_upgrade('my.package:default', ('1001',), description)
        note.set_transaction_note()

        # Prevent from printing the very long description in the assertion
        # message by not using assertIn..
        assert 'AAAA' not in transaction.get().description, \
            'Description seems not to be removed from too long' + \
            ' transaction note.'

        self.assertEquals(
            u'my.package:default -> 1000\n'
            u'my.package:default -> 1001',
            transaction.get().description)

    def test_cropped_when_too_long_even_without_description(self):
        profileid = 'my.package:default'

        transaction.get().note('Some notes..')

        note = TransactionNote()
        for destination in range(1, (65533 / len(profileid)) + 2):
            note.add_upgrade(profileid, (str(destination),), '')
        note.set_transaction_note()

        result = transaction.get().description
        expected_start = 'Some notes..\nmy.package:default -> 1\n'
        self.assertTrue(
            result.startswith(expected_start),
            ('Expected transaction note to start with "%s",'
             ' but it started with "%s"') % (
                expected_start, result[:50]))

        self.assertTrue(
            result.endswith('...'),
            'Expected transaction note to be cropped, ending with "..." '
            'but it ends with "%s"' % result[-30:])
