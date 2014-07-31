import unittest
import logging
from nose.plugins.attrib import attr

from tests.common import get_check

logging.basicConfig()

CONFIG = """
init_config:

instances:
    -   host: .
        tags:
            - mytag1
            - mytag2
"""

class IISTestCase(unittest.TestCase):
    @attr('windows')
    def testIIS(self):
        check, instances = get_check('iis', CONFIG)
        check.check(instances[0])
        metrics = check.get_metrics()
        service_checks = check.get_service_checks()

        # Second run to get the rates
        check.check(instances[0])
        metrics = check.get_metrics()
        service_checks = check.get_service_checks()

        base_metrics = [m[0] for m in check.METRICS]
        ret_metrics = [m[0] for m in metrics]
        ret_tags = [m[3]['tags'] for m in metrics]

        # Make sure each metric was captured
        for metric in base_metrics:
            self.assertTrue(metric in ret_metrics, "not reporting %s" % metric)

        # Make sure everything is tagged correctly
        for tags in ret_tags:
            self.assertEquals(assert tags == ['mytag1', 'mytag2'], tags)

        # Make sure that we get a service check
        self.assertEquals(len(service_checks),1)
        self.assertEquals(check.SERVICE_CHECK, service_checks[0]['check'])
        self.assertEquals(['site:Default Web Site'], service_checks[0]['tags'])


if __name__ == "__main__":
    unittest.main()
