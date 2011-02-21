import unittest
import logging; logger = logging.getLogger()

import MySQLdb
from checks.db.mysql import MySql

class TestMySql(unittest.TestCase):
    def setUp(self):
        self.mock = MySQLdb.MockSql()
        self.mysql = MySql(logger)

    def testChecks(self):
        # First round for gauges
        results = self.mysql.check({"MySQLServer": "blah", "MySQLUser": "blah", "MySQLPass": "blah"})
        self.assertEquals(results["mysqlCreatedTmpDiskTables"], 2.0)
        self.assertEquals(results["mysqlMaxUsedConnections"], 5.0)
        self.assertEquals(results["mysqlOpenFiles"], 6.0)
        self.assertEquals(results["mysqlTableLocksWaited"], 7.0)
        self.assertEquals(results["mysqlThreadsConnected"], 8.0)
        self.assertEquals(results["mysqlSecondsBehindMaster"], 9.0)
        self.assertEquals("mysqlSlowQueries" not in results, True)
        self.assertEquals("mysqlQuestions" not in results, True)

        # Add 2 counters
        results = self.mysql.check({"MySQLServer": "blah", "MySQLUser": "blah", "MySQLPass": "blah"})
        self.assertEquals(results["mysqlConnections"], 0.0)
        self.assertEquals(results["mysqlSlowQueries"], 0.0)
        self.assertEquals(results["mysqlQuestions"], 0.0)

        # same values
        self.assertEquals(results["mysqlCreatedTmpDiskTables"], 2.0)
        self.assertEquals(results["mysqlMaxUsedConnections"], 5.0)
        self.assertEquals(results["mysqlOpenFiles"], 6.0)
        self.assertEquals(results["mysqlTableLocksWaited"], 7.0)
        self.assertEquals(results["mysqlThreadsConnected"], 8.0)
        self.assertEquals(results["mysqlSecondsBehindMaster"], 9.0)

if __name__ == '__main__':
    unittest.main()
