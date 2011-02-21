import unittest
import logging
logging.basicConfig()
logger = logging.getLogger()

from checks.db.mongo import MongoDb

class TestMongo(unittest.TestCase):
    def setUp(self):
        self.c = MongoDb(logger)

    def testCheck(self):
        r = self.c.check({"MongoDBServer": "blah"})
        self.assertEquals(r["connections"]["current"], 1)
        self.assertEquals("opcounters" in r, False)

        r = self.c.check({"MongoDBServer": "blah"})
        self.assertEquals(r["connections"]["current"], 1)
        self.assertEquals(r["asserts"]["regularPS"], 0)
        self.assertEquals(r["asserts"]["userPS"], 0)
        self.assertEquals(r["opcounters"]["commandPS"], (244 - 18) / (10191 - 2893))
        

if __name__ == '__main__':
    unittest.main()
        
