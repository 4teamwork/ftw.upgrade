from AccessControl.SecurityInfo import ClassSecurityInformation
from time import time

import logging
import six


class ProgressLogger(object):
    """Loggs the proggress of a process to the passed
    logger.
    """

    security = ClassSecurityInformation()

    def __init__(self, message, iterable, logger=None,
                 timeout=5):
        self.logger = logger or logging.getLogger('ftw.upgrade')
        self.message = message
        self.iterable = iterable

        if isinstance(iterable, (six.integer_types + (float,))):
            self.length = iterable
        else:
            self.length = len(iterable)

        self.timeout = timeout
        self._timestamp = None
        self._counter = 0
        self._current_item = None

    security.declarePrivate('__enter__')
    def __enter__(self):
        self.logger.info('STARTING %s' % self.message)
        return self

    security.declarePrivate('__exit__')
    def __exit__(self, exc_type, exc_value, traceback):
        if not exc_type:
            self.logger.info('DONE %s' % self.message)

        else:
            if self._current_item is not None:
                current_step = repr(self._current_item)
            else:
                current_step = 'item nr. %d' % self._counter

            self.logger.error('FAILED %s (%s: %s) at %s' % (
                    self.message,
                    str(exc_type.__name__),
                    str(exc_value),
                    current_step))

    security.declarePrivate('__call__')
    def __call__(self):
        self._counter += 1
        if not self.should_be_logged():
            return

        percent = int(self._counter * 100.0 / self.length)
        self.logger.info('%s of %s (%s%%): %s' % (
                self._counter,
                self.length,
                percent,
                self.message))

    security.declarePrivate('__iter__')
    def __iter__(self):
        with self as step:
            for item in self.iterable:
                self._current_item = item
                yield item
                step()

    security.declarePrivate('should_be_logged')
    def should_be_logged(self):
        now = float(time())

        if self._timestamp is None:
            self._timestamp = now
            return True

        next_stamp = self._timestamp + self.timeout
        if next_stamp <= now:
            self._timestamp = now
            return True

        else:
            return False
