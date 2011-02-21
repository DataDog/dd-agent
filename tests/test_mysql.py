import unittest
import logging; logger = logging.getLogger()

import MySQLdb
from checks.db.mysql import MySql

class TestMySql(unittest.TestCase):
    def setUp(self):
        self.mock = MySQLdb.MockSql()
        self.mysql = MySql(logger)

    def testChecks(self):
        results = self.mysql.check({"MySQLServer": "blah", "MySQLUser": "blah", "MySQLPass": "blah"})
        self.assertEquals(len(results), 9, results)
        self.assertEquals(results["mysqlConnections"], 1.0)
        self.assertEquals(results["mysqlCreatedTmpDiskTables"], 2.0)
        self.assertEquals(results["mysqlSlowQueries"], 0.0)
        self.assertEquals(results["mysqlQueries"], 0.0)
        self.assertEquals(results["mysqlMaxUsedConenctions"], 5.0)
        self.assertEquals(results["mysqlOpenFiles"], 6.0)
        self.assertEquals(results["mysqlTableLocksWaited"], 7.0)
        self.assertEquals(results["mysqlThreadsConnected"], 8.0)
        self.assertEquals(results["mysqlSecondsBehindMaster"], 9.0)

if __name__ == '__main__':
    unittest.main()
