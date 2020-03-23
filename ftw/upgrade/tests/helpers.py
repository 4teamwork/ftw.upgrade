from contextlib import contextmanager

import logging
import os
import sys


@contextmanager
def capture_streams(stdout=None, stderr=None):
    ori_stdout = sys.stdout
    ori_stderr = sys.stderr

    if stdout is not None:
        sys.stdout = stdout
    if stderr is not None:
        sys.stderr = stderr

    try:
        yield
    finally:
        if stdout is not None:
            sys.stdout = ori_stdout
        if stderr is not None:
            sys.stderr = ori_stderr


@contextmanager
def chdir(path):
    before = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(before)


@contextmanager
def verbose_logging():
    original_level = logging.root.getEffectiveLevel()
    logging.root.setLevel(logging.INFO)
    try:
        yield

    finally:
        logging.root.setLevel(original_level)


@contextmanager
def no_logging_threads():
    """In testing, when a request is executed (e.g. from requests) to the ZSERVER
    layer and errors are logged, the logging module might write to the logging
    handler in a thread after the request is finished.
    Since the testrunner tracks left over threads the logging thread is detected
    as leftover thread. Since this thread is a dummy thread it cannot be joined,
    which results in a error in the threading module (python 2.7 bug).
    The result is that from this test on the test log is spammed with threading
    errors for each following test.
    In order to mitigate this issue this context manager temporarily disables
    threading of logging in general so that logs are processed synchronously and
    no left over threads are created.
    """
    original_log_threads = logging.logThreads
    logging.logThreads = 0
    try:
        yield
    finally:
        logging.logThreads = original_log_threads
