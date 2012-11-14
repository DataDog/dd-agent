import unittest
import logging; logger = logging.getLogger()

from checks.db.mysql import MySql

class TestMySql(unittest.TestCase):
    def setUp(self):
        # This should run on pre-2.7 python so no skiptest
        try:
            import MySQLdb
            self.mysql = MySql(logger)
        except ImportError:
            self.skip = True

    def testChecks(self):
        if not self.skip:
            results = self.mysql.check({"mysql_server": "localhost", "mysql_user": "dog", "mysql_pass": "dog"})
            assert results

if __name__ == '__main__':
    unittest.main()
