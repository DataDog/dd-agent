import unittest
import logging
from nose.plugins.attrib import attr

from checks import gethostname
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

@attr('windows')
class IISTestCase(unittest.TestCase):
    def testIIS(self):
        check, instances = get_check('iis', CONFIG)
        check.check(instances[0])
        metrics = check.get_metrics()

        base_metrics = [m[0] for m in check.METRICS]
        ret_metrics = [m[0] for m in metrics]
        ret_tags = [m[3]['tags'] for m in metrics]

        # Make sure each metric was captured
        for metric in base_metrics:
            assert metric in ret_metrics

        # Make sure everything is tagged correctly
        for tags in ret_tags:
            assert tags == ['mytag1', 'mytag2']

if __name__ == "__main__":
    unittest.main()