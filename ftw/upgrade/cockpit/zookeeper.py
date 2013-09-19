from ftw.upgrade.api.json_api import PROGRESS_MARKER
from ftw.upgrade.cockpit.exceptions import AllWorkersFinished
from ftw.upgrade.utils import list_buildouts
from ftw.upgrade.utils import py_interpreter_from_shebang
from multiprocessing import Pipe
from multiprocessing import Process
from multiprocessing import Queue
from subprocess import Popen, PIPE
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


class ZooKeeper(object):
    """Takes care of spawning multiple worker processes that run upgrades for
    a single Plone buildout and keeps track of their progress.
    """

    def __init__(self, cluster_dir, runner_class=None):
        self.cluster_dir = cluster_dir
        self.workers = []
        if not runner_class:
            self.runner_class = UpgradeRunner
        else:
            self.runner_class = runner_class

    @property
    def buildouts(self):
        return list_buildouts(self.cluster_dir)

    def spawn_runners(self):
        """Spawns subprocesses that run upgrades.
        """
        self.status = Queue()

        # Set up a pipe for worker processes to signal available updates
        # back to the main process
        self.parent_conn, self.child_conn = Pipe(duplex=False)

        runner = self.runner_class(self.cluster_dir)

        for n, buildout in enumerate(self.buildouts):
            child = Process(target=runner.upgrade,
                            args=(self.status, n + 1, buildout, self.child_conn))
            child.start()
            self.workers.append(child)

    def clean_up_runners(self):
        # Create a copy so we don't change list size during iteration
        for runner in self.workers[:]:
            runner.join()
            self.workers.remove(runner)

    def poll_progress_info(self):
        """Method that checks, if any workers are still alive, whether there's
        progress updates in the shared queue.

        If progress updates are available, they will be handed to the
        update_progress() method.
        """
        if any(w.is_alive() for w in self.workers):
            while not self.status.empty():
                worker_number, progress = self.status.get()
                self.update_progress((worker_number, progress))
        else:
            # All processes terminated. Process any remaining progress
            # updates from the queue
            while not self.status.empty():
                worker_number, progress = self.status.get()
                self.update_progress((worker_number, progress))
            raise AllWorkersFinished()

    def update_progress(self, progress_info):
        raise NotImplementedError()


class MockZooKeeper(ZooKeeper):
    """Mock of a ZooKeeper - doesn't run any upgrades, but still spawns
    processes and reports some faked progress info.
    """
    def __init__(self, cluster_dir, runner_class=None):
        self.cluster_dir = cluster_dir
        self.workers = []
        self.runner_class = FakeUpgradeRunner

    @property
    def buildouts(self):
        return ['Worker-%s' % n for n in range(20)]

    def poll_progress_info(self):
        """Method that checks, if any workers are still alive, whether there's
        progress updates in the shared queue.

        If progress updates are available, they will be handed to the
        update_progress() method.
        """
        if any(w.is_alive() for w in self.workers):
            while not self.status.empty():
                worker_number, progress = self.status.get()
                self.update_progress((worker_number, progress))
        else:
            # All processes terminated. Process any remaining progress
            # updates from the queue
            while not self.status.empty():
                worker_number, progress = self.status.get()
                self.update_progress((worker_number, progress))
            raise AllWorkersFinished()


class SimpleClusterUpgrader(ZooKeeper):
    """This is a most basic implementation of a controller that upgrades a
    Plone site cluster by running upgrades in parallel.

    It's main purpose is for (manual) testing, debugging and forcing us to keep
    UI code and business logic well separated.

    It runs upgrades for all buildouts using the UpgradeRunner and reports the
    individual runners' progress by simply printing out
    <runner_number>, <progress> pairs as soon as progress updates arrive.
    """

    def __init__(self, cluster_dir):
        ZooKeeper.__init__(self, cluster_dir)

    def run(self):
        self.spawn_runners()
        while True:
            try:
                self.poll_progress_info()
            except AllWorkersFinished:
                break
        self.clean_up_runners()

    def update_progress(self, progress_info):
        worker_number, progress = progress_info
        print "%s, %s" % (worker_number, progress)
