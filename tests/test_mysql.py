import unittest
from tests.common import load_check
from nose.plugins.attrib import attr
import time

@attr(requires='mysql')
class TestMySql(unittest.TestCase):
    def setUp(self):
        # This should run on pre-2.7 python so no skiptest
        self.skip = False
        try:
            import pymysql
        except ImportError:
            self.skip = True

    def testChecks(self):
        if not self.skip:
            agentConfig = {
                'version': '0.1',
                'api_key': 'toto' }

            conf = {'init_config': {}, 'instances': [{
                'server': 'localhost',
                'user': 'dog',
                'pass': 'dog',
                'options': {'replication': True},
            }]}
            # Initialize the check from checks.d
            self.check = load_check('mysql', conf, agentConfig)

            self.check.run()
            metrics = self.check.get_metrics()
            self.assertTrue(len(metrics) >= 8, metrics)

            # Service checks
            service_checks = self.check.get_service_checks()
            service_checks_count = len(service_checks)
            self.assertTrue(type(service_checks) == type([]))
            self.assertTrue(service_checks_count > 0)
            self.assertEquals(len([sc for sc in service_checks if sc['check'] == self.check.SERVICE_CHECK_NAME]), 1, service_checks)
            # Assert that all service checks have the proper tags: host and port
            self.assertEquals(len([sc for sc in service_checks if "host:localhost" in sc['tags']]), service_checks_count, service_checks)
            self.assertEquals(len([sc for sc in service_checks if "port:0" in sc['tags']]), service_checks_count, service_checks)

            # Flush previous metadata
            self.check.get_service_metadata()

            time.sleep(1)
            self.check.run()
            metrics = self.check.get_metrics()
            self.assertTrue(len(metrics) >= 16, metrics)

            # Service metadata
            service_metadata = self.check.get_service_metadata()
            service_metadata_count = len(service_metadata)
            self.assertTrue(service_metadata_count > 0)
            for meta_dict in service_metadata:
                assert meta_dict



if __name__ == '__main__':
    unittest.main()
