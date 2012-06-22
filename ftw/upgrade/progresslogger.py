from time import time
import logging


class ProgressLogger(object):
    """Loggs the proggress of a process to the passed
    logger.
    """

    def __init__(self, message, iterable, logger=None,
                 timeout=5):
        self.logger = logger or logging.getLogger('ftw.upgrade')
        self.message = message

        if isinstance(iterable, (int, long, float)):
            self.length = iterable
        else:
            self.length = len(iterable)

        self.timeout = timeout
        self._timestamp = None
        self._counter = 0

    def __enter__(self):
        self.logger.info('STARTING %s' % self.message)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if not exc_type:
            self.logger.info('DONE %s' % self.message)

        else:
            self.logger.error('FAILED %s (%s: %s)' % (
                    self.message,
                    str(exc_type.__name__),
                    str(exc_value)))

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
