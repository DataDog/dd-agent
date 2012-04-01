import unittest
import logging
logging.basicConfig()
import subprocess
from tempfile import mkdtemp

from checks.db.mongo import MongoDb

PORT1 = 27017
PORT2 = 37017

class TestMongo(unittest.TestCase):
    def setUp(self):
        self.c = MongoDb(logging.getLogger())
        # Start 1 instances of Mongo
        dir1 = mkdtemp()
        self.p1 = subprocess.Popen(["mongod", "--dbpath", dir1, "--port", str(PORT1)],
                                   executable="mongod",
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)

    def tearDown(self):
        if self.p1 is not None:
            self.p1.terminate()

    def testCheck(self):
        if self.p1 is not None:
            r = self.c.check({"MongoDBServer": "localhost", "mongodb_port": PORT1})
            self.assertEquals(r and r["connections"]["current"] == 1, True)
            assert r["connections"]["available"] >= 1
            assert r["uptime"] >= 0, r
            assert r["mem"]["resident"] > 0
            assert r["mem"]["virtual"] > 0

if __name__ == '__main__':
    unittest.main()
        
