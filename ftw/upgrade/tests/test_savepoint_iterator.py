from ftw.upgrade.testing import UPGRADE_FUNCTIONAL_TESTING
from ftw.upgrade.utils import SavepointIterator
from unittest import TestCase

import os
import transaction


class TestSavepointIterator(TestCase):
    layer = UPGRADE_FUNCTIONAL_TESTING

    def setUp(self):
        super(TestSavepointIterator, self).setUp()
        self.iterable = [1, 2, 3, 4, 5]
        self.txn = transaction.get()

    def tearDown(self):
        self.txn.abort()
        os.environ.pop('UPGRADE_SAVEPOINT_THRESHOLD', None)

    def test_creates_savepoints(self):
        self.assertEqual(
            0, self.txn._savepoint_index,
            'A new transaction should not have any savepoints yet')

        iterator = SavepointIterator.build(self.iterable, threshold=5)

        # Consume entire iterator
        result = list(iterator)

        self.assertEqual(
            self.iterable, result,
            'Iterator should yield every item of `iterable`')

        self.assertEqual(
            1, self.txn._savepoint_index,
            'One savepoint should have been created')

    def test_doesnt_create_savepoints_with_threshold_0(self):
        self.assertEqual(
            0, self.txn._savepoint_index,
            'A new transaction should not have any savepoints yet')

        iterator = SavepointIterator.build(self.iterable, threshold=0)

        # Consume entire iterator
        result = list(iterator)

        self.assertEqual(
            self.iterable, result,
            'Iterator should yield every item of `iterable`')

        self.assertEqual(
            0, self.txn._savepoint_index,
            'threshold=0 should never create any savepoints')

    def test_instanciating_iterator_with_nonzero_threshold_raises(self):
        with self.assertRaises(ValueError):
            SavepointIterator(self.iterable, threshold=0)

        with self.assertRaises(ValueError):
            SavepointIterator(self.iterable, threshold=None)

    def test_default_threshold_is_1000(self):
        # 1000 is the application default.
        self.assertEqual(1000, SavepointIterator.get_default_threshold())

    def test_configure_default_threshold_with_environ_variable(self):
        os.environ['UPGRADE_SAVEPOINT_THRESHOLD'] = '333'
        self.assertEqual(333, SavepointIterator.get_default_threshold())

    def test_disable_default_threshold_with_environ_variable(self):
        os.environ['UPGRADE_SAVEPOINT_THRESHOLD'] = 'None'
        self.assertIsNone(SavepointIterator.get_default_threshold())
        os.environ['UPGRADE_SAVEPOINT_THRESHOLD'] = 'none'
        self.assertIsNone(SavepointIterator.get_default_threshold())

    def test_invalid_default_thresold_configuration(self):
        os.environ['UPGRADE_SAVEPOINT_THRESHOLD'] = 'foo'
        with self.assertRaises(ValueError) as cm:
            SavepointIterator.get_default_threshold()
        self.assertEqual("Invalid savepoint threshold 'foo'", str(cm.exception))
