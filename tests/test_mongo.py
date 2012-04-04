import unittest
import logging
logging.basicConfig()
import subprocess
from tempfile import mkdtemp
import time
import socket

import pymongo
from checks.db.mongo import MongoDb

PORT1 = 27017
PORT2 = 27018
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
        self.c = MongoDb(logging.getLogger())
        # Start 2 instances of Mongo in a replica set
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
                c1 = pymongo.Connection('localhost:%s' % PORT1, slave_okay=True)
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
        except:
            logging.getLogger().exception("Cannot instantiate mongod properly")

    def tearDown(self):
        try:
            if "p1" in dir(self): self.p1.terminate()
            if "p2" in dir(self): self.p2.terminate()
        except:
            logging.getLogger().exception("Cannot terminate mongod instances")

    def testCheck(self):
        r = self.c.check({"MongoDBServer": "localhost", "mongodb_port": PORT1})
        self.assertEquals(r and r["connections"]["current"] >= 1, True)
        assert r["connections"]["available"] >= 1
        assert r["uptime"] >= 0, r
        assert r["mem"]["resident"] > 0
        assert r["mem"]["virtual"] > 0
        assert "replSet" in r

        r = self.c.check({"MongoDBServer": "localhost", "mongodb_port": PORT2})
        self.assertEquals(r and r["connections"]["current"] >= 1, True)
        assert r["connections"]["available"] >= 1
        assert r["uptime"] >= 0, r
        assert r["mem"]["resident"] > 0
        assert r["mem"]["virtual"] > 0
        assert "replSet" in r
            

if __name__ == '__main__':
    unittest.main()
        
