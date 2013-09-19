from ftw.upgrade.cockpit.cluster import ZooKeeper
from unittest2 import TestCase
import os
import shutil


def touch(fname, times=None):
    with file(fname, 'a'):
        os.utime(fname, times)


class TestZookeeper(TestCase):

    def setUp(self):
        self.buildouts = ['b1', 'b2', 'b3']
        cwd = os.getcwd()
        self.test_cluster_dir = os.path.join(cwd, "test_cluster_dir")
        os.mkdir(self.test_cluster_dir)
        for buildout in self.buildouts:
            bin_dir = os.path.join(self.test_cluster_dir, buildout, 'bin')
            os.makedirs(bin_dir)
            touch(os.path.join(bin_dir, 'buildout'))

    def tearDown(self):
        shutil.rmtree(self.test_cluster_dir)

    def test_zookeeper_lists_buildouts(self):
        zookeeper = ZooKeeper(self.test_cluster_dir)
        self.assertEquals(zookeeper.buildouts, self.buildouts)