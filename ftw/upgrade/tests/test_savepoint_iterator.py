from ftw.upgrade.utils import SavepointIterator
from unittest2 import TestCase
import transaction


class TestSavepointIterator(TestCase):

    def setUp(self):
        self.iterable = [1, 2, 3, 4, 5]
        self.txn = transaction.get()

    def tearDown(self):
        self.txn.abort()

    def test_creates_savepoints(self):
        self.assertEquals(
            0, self.txn._savepoint_index,
            'A new transaction should not have any savepoints yet')

        iterator = SavepointIterator.build(self.iterable, threshold=5)

        # Consume entire iterator
        result = list(iterator)

        self.assertEquals(
            self.iterable, result,
            'Iterator should yield every item of `iterable`')

        self.assertEquals(
            1, self.txn._savepoint_index,
            'One savepoint should have been created')

    def test_doesnt_create_savepoints_with_threshold_0(self):
        self.assertEquals(
            0, self.txn._savepoint_index,
            'A new transaction should not have any savepoints yet')

        iterator = SavepointIterator.build(self.iterable, threshold=0)

        # Consume entire iterator
        result = list(iterator)

        self.assertEquals(
            self.iterable, result,
            'Iterator should yield every item of `iterable`')

        self.assertEquals(
            0, self.txn._savepoint_index,
            'threshold=0 should never create any savepoints')

    def test_instanciating_iterator_with_nonzero_threshold_raises(self):
        with self.assertRaises(ValueError):
            SavepointIterator(self.iterable, threshold=0)

        with self.assertRaises(ValueError):
            SavepointIterator(self.iterable, threshold=None)
