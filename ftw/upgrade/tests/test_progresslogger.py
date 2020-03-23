from ftw.upgrade.progresslogger import ProgressLogger
from six import StringIO
from six.moves import range
from time import sleep
from unittest import TestCase

import logging


class TestProgressLogger(TestCase):

    def setUp(self):
        self.log = StringIO()
        self.logger = logging.getLogger('ftw.upgrade')
        self.logger.setLevel(logging.DEBUG)

        handler = logging.StreamHandler(self.log)
        self.logger.addHandler(handler)

    def read_log(self):
        self.log.seek(0)
        return self.log.read().strip().split('\n')

    def test_succeeding_logging(self):
        with ProgressLogger('Foo', 5, logger=self.logger,
                            timeout=0.03) as step:
            for i in range(5):
                step()
                sleep(0.0151)

        self.assertEqual(['STARTING Foo',
                          '1 of 5 (20%): Foo',
                          '3 of 5 (60%): Foo',
                          '5 of 5 (100%): Foo',
                          'DONE Foo'],
                         self.read_log())

    def test_failing_logging(self):
        timeout = 0

        with self.assertRaises(ValueError):

            data = list(range(5))

            with ProgressLogger('Bar', data, logger=self.logger,
                                timeout=timeout) as step:
                for i in data:
                    if i == 3:
                        raise ValueError('baz')

                    step()

        self.assertEqual(['STARTING Bar',
                          '1 of 5 (20%): Bar',
                          '2 of 5 (40%): Bar',
                          '3 of 5 (60%): Bar',
                          'FAILED Bar (ValueError: baz) at item nr. 3'],
                         self.read_log())

    def test_accepts_iterable_object(self):
        items = list(range(5))

        with ProgressLogger('Foo', items, logger=self.logger) as step:
            for _item in items:
                step()

        self.assertEqual(['STARTING Foo',
                          '1 of 5 (20%): Foo',
                          'DONE Foo'],
                         self.read_log())

    def test_acts_as_iterable_wrapper(self):
        items = list(range(5))

        result = []

        for item in ProgressLogger('Foo', items, logger=self.logger):
            result.append(item)

        self.assertEqual(['STARTING Foo',
                          '1 of 5 (20%): Foo',
                          'DONE Foo'],
                         self.read_log())

        self.assertEqual(
            items, result,
            'Iterating over the progresslogger yields the original items.')

    def test_current_item_is_printed_when_logger_exits_unexpectedly(self):
        items = list(range(5))

        with self.assertRaises(ValueError):
            for item in ProgressLogger('Foo', items, logger=self.logger):
                if item == 4:
                    raise ValueError('baz')

        self.assertEqual(['STARTING Foo',
                          '1 of 5 (20%): Foo',
                          'FAILED Foo (GeneratorExit: ) at 4'],
                         self.read_log())
