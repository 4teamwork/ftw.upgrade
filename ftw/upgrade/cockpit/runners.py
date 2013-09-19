from ftw.upgrade.api.json_api import PROGRESS_MARKER
from ftw.upgrade.utils import py_interpreter_from_shebang
from subprocess import PIPE
from subprocess import Popen
import os
import random
import re
import time


class UpgradeRunner(object):
    """Runs upgrades for a single Plone buildout by spawning a new subprocess,
    and relaying its progress info to STDOUT (unbuffered).
    """

    def __init__(self, cluster_dir):
        self.cluster_dir = cluster_dir

    def upgrade(self, status, n, buildout_name, conn):
        instance_path = os.path.abspath(
            os.path.join(self.cluster_dir, buildout_name, 'bin', 'instance'))
        python_interpreter = py_interpreter_from_shebang(instance_path)
        python_args = '-u'
        upgrade_args = "--progress-info run-all-upgrades"
        upgrade_cmd = "%s %s %s upgrade_http %s" % (
            python_interpreter, python_args, instance_path, upgrade_args)

        p = Popen(upgrade_cmd, shell=True, stdout=PIPE, bufsize=1)
        for line in iter(p.stdout.readline, b''):
            if line.startswith(PROGRESS_MARKER):
                pattern = re.compile('%s: ([0-9]*/[0-9]*)' % PROGRESS_MARKER)
                progress_current, progress_total = pattern.match(line).group(1).split('/')
                progress = float(progress_current) / float(progress_total)
                status.put([n, progress])
                conn.send(True)
        p.communicate()


class FakeUpgradeRunner(object):
    """Simulates some random progress info output for testing.

    Like the real thing, it communicates its progress info by writing it to the
    shared `status` queue and signalling progress updates by writing to the
    end of a pipe identified by `conn`.
    """

    def __init__(self, unused_cluster_dir):
        pass

    def upgrade(self, status, n, buildout_name, conn):
        count = random.randint(5, 30)
        for i in range(count):
            status.put([n, (i+1.0)/count])
            conn.send(True)
            time.sleep(random.random())


class TestingUpgradeRunner(object):
    """Simulates some random progress info output for automated testing.

    Like the real thing, it communicates its progress info by writing it to the
    shared `status` queue and signalling progress updates by writing to the
    end of a pipe identified by `conn`.
    """

    def __init__(self, unused_cluster_dir, steps=5):
        self.steps = steps

    def upgrade(self, status, n, buildout_name, conn):
        count = self.steps
        for i in range(count):
            status.put([n, (i + 1.0) / count])
            conn.send(True)
