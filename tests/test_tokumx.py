import unittest
import logging
import subprocess
from tempfile import mkdtemp
import time
import socket

import pymongo

from tests.common import load_check

PORT1 = 37017
PORT2 = 37018
MAX_WAIT = 150

class TestMongo(unittest.TestCase):
    def wait4mongo(self, process, port):
        # Somehow process.communicate() hangs
        out = process.stdout
        loop = 0
        while True:
            l = out.readline()
            if l.find("[initandlisten] waiting for connections on port") > -1:
                break
            else:
                time.sleep(0.1)
                loop += 1
                if loop >= MAX_WAIT:
                    break

    def setUp(self):
        self.agentConfig = {
            'version': '0.1',
            'api_key': 'toto'
        }

        # Initialize the check from checks.d
        self.check = load_check('tokumx', {'init_config': {}, 'instances': {}}, self.agentConfig)

        # Start 2 instances of TokuMX in a replica set
        dir1 = mkdtemp()
        dir2 = mkdtemp()
        try:
            self.p1 = subprocess.Popen(["mongod", "--dbpath", dir1, "--port", str(PORT1), "--replSet", "testset/%s:%d" % (socket.gethostname(), PORT2), "--rest"],
                                       executable="mongod",
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE)
            # Sleep until mongo comes online
            self.wait4mongo(self.p1, PORT1)
            if self.p1:
                # Set up replication
                c1 = pymongo.Connection('localhost:%s' % PORT1, read_preference=pymongo.ReadPreference.PRIMARY_PREFERRED)
                self.p2 = subprocess.Popen(["mongod", "--dbpath", dir2, "--port", str(PORT2), "--replSet", "testset/%s:%d" % (socket.gethostname(), PORT1), "--rest"],
                                           executable="mongod",
                                           stdout=subprocess.PIPE,
                                           stderr=subprocess.PIPE)
                self.wait4mongo(self.p2, PORT2)
                # Waiting before all members are online
                time.sleep(15)
                c1.admin.command("replSetInitiate")
                # Sleep for 15s until replication is stable
                time.sleep(30)
                x = c1.admin.command("replSetGetStatus")
                assert pymongo.Connection('localhost:%s' % PORT2)
        except Exception:
            logging.getLogger().exception("Cannot instantiate mongod properly")

    def tearDown(self):
        try:
            if "p1" in dir(self): self.p1.terminate()
            if "p2" in dir(self): self.p2.terminate()
        except Exception:
            logging.getLogger().exception("Cannot terminate mongod instances")

    def testMongoCheck(self):
        self.config = {
            'instances': [{
                'server': "mongodb://localhost:%s/test" % PORT1
            },
            {
                'server': "mongodb://localhost:%s/test" % PORT2
            }]
        }

        # Test mongodb with checks.d
        self.check = load_check('tokumx', self.config, self.agentConfig)

        # Run the check against our running server
        self.check.check(self.config['instances'][0])
        # Sleep for 1 second so the rate interval >=1
        time.sleep(1)
        # Run the check again so we get the rates
        self.check.check(self.config['instances'][0])

        # Metric assertions
        metrics = self.check.get_metrics()
        assert metrics
        self.assertTrue(type(metrics) == type([]))
        self.assertTrue(len(metrics) > 0)

        metric_val_checks = {
            'mongodb.connections.current': lambda x: x >= 1,
            'mongodb.connections.available': lambda x: x >= 1,
            'mongodb.uptime': lambda x: x >= 0,
            'mongodb.ft.cachetable.size.current': lambda x: x > 0,
            'mongodb.ft.cachetable.size.limit': lambda x: x > 0,
        }

        for m in metrics:
            metric_name = m[0]
            if metric_name in metric_val_checks:
                self.assertTrue( metric_val_checks[metric_name]( m[2] ) )

        # Run the check against our running server
        self.check.check(self.config['instances'][1])
        # Sleep for 1 second so the rate interval >=1
        time.sleep(1)
        # Run the check again so we get the rates
        self.check.check(self.config['instances'][1])

        # Metric assertions
        metrics = self.check.get_metrics()
        assert metrics
        self.assertTrue(type(metrics) == type([]))
        self.assertTrue(len(metrics) > 0)

        for m in metrics:
            metric_name = m[0]
            if metric_name in metric_val_checks:
                self.assertTrue( metric_val_checks[metric_name]( m[2] ) )

if __name__ == '__main__':
    unittest.main()
