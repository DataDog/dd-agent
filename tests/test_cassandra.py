import logging
import unittest
import os
import os.path

from nose.plugins.attrib import attr

from checks.cassandra import Cassandra



logger = logging.getLogger(__name__)

class TestCassandra(unittest.TestCase):
    def setUp(self):
        self.info = open(os.path.join(os.path.dirname(__file__), "cassandra", "info"), "r").read()
        self.info8 = open(os.path.join(os.path.dirname(__file__), "cassandra", "info.8"), "r").read()
        self.tpstats = open(os.path.join(os.path.dirname(__file__), "cassandra", "tpstats"), "r").read()
        self.tpstats8 = open(os.path.join(os.path.dirname(__file__), "cassandra", "tpstats.8"), "r").read()
        self.cfstats = open(os.path.join(os.path.dirname(__file__), "cassandra", "cfstats"), "r").read()
        self.info_opp = open(os.path.join(os.path.dirname(__file__), "cassandra", "info.opp"), "r").read()
        self.c = Cassandra()
        
    def tearDown(self):
        pass

    @attr('cassandra')
    def testParseInfoOpp(self):
        # Assert we can parse tokens from nodes using the order preserving
        # partitioner.
        res = {}
        self.c._parseInfo(self.info_opp, res, logger)
        self.assertNotEquals(len(res.keys()), 0)
        self.assertEquals(res.get("token"), 5.6713727820156407e+37)
#        self.assertEquals(res.get("load"), 304803091578.0)
#        self.assertEquals(res.get("uptime"), 188319)
#        self.assertEquals(res.get("heap_used"), 2527.04)
#        self.assertEquals(res.get("heap_total"), 3830.0)
#        self.assertEquals(res.get("datacenter"), 28)
#        self.assertEquals(res.get("rack"), 76)
#        self.assertEquals(res.get("exceptions"), 0)
#
        
    @attr('cassandra')
    def testParseInfo(self):
        res = {}
        # v0.7
        self.c._parseInfo(self.info, res, logger)
        self.assertNotEquals(len(res.keys()), 0)
        self.assertEquals(res.get("load"), 467988.0)
        self.assertEquals(res.get("token"), 3.6299342986353447e+37)
        self.assertEquals(res.get("uptime"), 95)
        self.assertEquals(res.get("heap_used"), 521.86)
        self.assertEquals(res.get("heap_total"), 1019.88)
        # v0.8
        res = {}
        self.c._parseInfo(self.info8, res, logger)
        self.assertNotEquals(len(res.keys()), 0)
        self.assertEquals(res.get("load"), 304803091578.0)
        self.assertEquals(res.get("token"), 5.102265587816026e+37)
        self.assertEquals(res.get("uptime"), 188319)
        self.assertEquals(res.get("heap_used"), 2527.04)
        self.assertEquals(res.get("heap_total"), 3830.0)
        self.assertEquals(res.get("datacenter"), 28)
        self.assertEquals(res.get("rack"), 76)
        self.assertEquals(res.get("exceptions"), 0)
        
    @attr('cassandra')
    def testParseCfstats(self):
        res = {}
        self.c._parseCfstats(self.cfstats, res)
        self.assertNotEquals(len(res.keys()), 0)
        
    @attr('cassandra')
    def testParseTpstats(self):
        res = {}
        self.c._parseTpstats(self.tpstats, res)
        self.assertNotEquals(len(res.keys()), 0)
        
if __name__ == '__main__':
    unittest.main()
