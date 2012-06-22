from StringIO import StringIO
from ftw.upgrade.progresslogger import ProgressLogger
from time import sleep
from unittest2 import TestCase
import  logging


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
        timeout = 0.01

        with ProgressLogger('Foo', 5, logger=self.logger,
                            timeout=timeout) as step:
            for i in range(5):
                step()
                sleep(timeout / 2)

        self.assertEqual(self.read_log(), [
                'STARTING Foo',
                '1 of 5 (20%): Foo',
                '3 of 5 (60%): Foo',
                '5 of 5 (100%): Foo',
                'DONE Foo'])

    def test_failing_logging(self):
        timeout = 0

        with self.assertRaises(ValueError):

            data = range(5)

            with ProgressLogger('Bar', data, logger=self.logger,
                                timeout=timeout) as step:
                for i in data:
                    if i == 3:
                        raise ValueError('baz')

                    step()

        self.assertEqual(self.read_log(), [
                'STARTING Bar',
                '1 of 5 (20%): Bar',
                '2 of 5 (40%): Bar',
                '3 of 5 (60%): Bar',
                'FAILED Bar (ValueError: baz)'])
