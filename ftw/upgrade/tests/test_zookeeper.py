from ftw.upgrade.cockpit.cluster import ZooKeeper
from ftw.upgrade.cockpit.cluster import TestingUpgradeRunner
from unittest2 import TestCase
import os
import shutil


def touch(fname, times=None):
    with file(fname, 'a'):
        os.utime(fname, times)


class TestZookeeper(TestCase):

    def setUp(self):
        self.buildouts = ['b1', 'b2', 'b3']
        self.testing_buildouts = []
        self.test_cluster_dir = os.path.join(os.getcwd(), "test_cluster_dir")
        self.create_test_buildouts(self.test_cluster_dir, self.buildouts)

    def create_test_buildouts(self, buildout_dir, buildouts):
        os.mkdir(buildout_dir)
        for buildout in buildouts:
            bin_dir = os.path.join(buildout_dir, buildout, 'bin')
            os.makedirs(bin_dir)
            touch(os.path.join(bin_dir, 'buildout'))
        self.testing_buildouts.append(buildout_dir)

    def remove_testing_buildouts(self):
        for path in self.testing_buildouts:
            shutil.rmtree(path)

    def tearDown(self):
        self.remove_testing_buildouts()


    def test_zookeeper_lists_buildouts(self):
        zookeeper = ZooKeeper(self.test_cluster_dir)
        self.assertEquals(zookeeper.buildouts, self.buildouts)

    def test_spawn_runners_spawns_one_worker_per_buildout(self):
        zookeeper = ZooKeeper(self.test_cluster_dir,
                              runner_class=TestingUpgradeRunner)
        zookeeper.spawn_runners()
        self.assertEquals(len(zookeeper.workers), len(self.buildouts))
        zookeeper.clean_up_runners()

    def test_clean_up_runners_cleans_up_all_workers(self):
        zookeeper = ZooKeeper(self.test_cluster_dir,
                              runner_class=TestingUpgradeRunner)
        zookeeper.spawn_runners()
        zookeeper.clean_up_runners()
        self.assertEquals(zookeeper.workers, [])

    def test_runners_report_progress_to_queue(self):
        buildout_dir = os.path.join(os.getcwd(), 'single_worker')
        self.create_test_buildouts(buildout_dir, ['b1'])

        zookeeper = ZooKeeper(buildout_dir,
                              runner_class=TestingUpgradeRunner)
        zookeeper.spawn_runners()

        # TestingUpgradeRunner emits exactly 5 progress updates
        queue = [zookeeper.status.get() for i in range(5)]
        self.assertEquals(queue, [[1, 0.2],
                                  [1, 0.4],
                                  [1, 0.6],
                                  [1, 0.8],
                                  [1, 1.0]])

        zookeeper.clean_up_runners()

    def test_runners_signal_progress_updates(self):
        buildout_dir = os.path.join(os.getcwd(), 'single_worker')
        self.create_test_buildouts(buildout_dir, ['b1'])

        zookeeper = ZooKeeper(buildout_dir,
                              runner_class=TestingUpgradeRunner)
        zookeeper.spawn_runners()

        # TestingUpgradeRunner emits exactly 5 progress updates
        signals = [zookeeper.parent_conn.recv() for i in range(5)]
        self.assertEquals(signals, [True] * 5)
        zookeeper.clean_up_runners()