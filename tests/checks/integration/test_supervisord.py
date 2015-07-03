# stdlib
import os
from time import sleep
import unittest

# 3p
from nose.plugins.attrib import attr

# project
from tests.checks.common import get_check


@attr(requires='supervisord')
class TestSupervisordCheck(unittest.TestCase):

    def test_travis_supervisord(self):
        """Integration test for supervisord check. Using a supervisord on Travis."""

        # Load yaml config
        config_str = open(os.environ['VOLATILE_DIR'] + '/supervisor/supervisord.yaml', 'r').read()
        self.assertTrue(config_str is not None and len(config_str) > 0, msg=config_str)

        # init the check and get the instances
        check, instances = get_check('supervisord', config_str)
        self.assertTrue(check is not None, msg=check)
        self.assertEquals(len(instances), 1)

        # Supervisord should run 3 programs for 30, 60 and 90 seconds
        # respectively. The tests below will ensure that the process count
        # metric is reported correctly after (roughly) 10, 40, 70 and 100 seconds
        for i in range(4):
            try:
                # Run the check
                check.check(instances[0])
            except Exception, e:
                # Make sure that it ran successfully
                self.assertTrue(False, msg=str(e))
            else:
                up, down = 0, 0
                for name, timestamp, value, meta in check.get_metrics():
                    if name == 'supervisord.process.count':
                        if 'status:up' in meta['tags']:
                            up = value
                        elif 'status:down' in meta['tags']:
                            down = value
                self.assertEquals(up, 3 - i)
                self.assertEquals(down, i)
                sleep(10)
