# stdlib
import time
import types

# 3p
import unittest

# project
from util import EC2


class TestEC2(unittest.TestCase):

    def test_metadata(self):
        # Reset metadata just to be sure
        EC2.metadata = {}
        # Test gathering metadata from ec2
        start = time.time()
        d = EC2.get_metadata({'collect_instance_metadata': True})
        end = time.time()
        self.assertTrue(isinstance(d, types.DictType))
        # Either we're on ec2 or we're not (at least 7 attributes expected)
        assert len(d) == 0 or len(d) >= 7, d
        if "instance-id" in d:
            assert d["instance-id"].startswith("i-"), d
        assert end - start <= 1.1, "It took %s seconds to get ec2 metadata" % (end-start)

    def test_is_default_hostname(self):
        for hostname in ['ip-172-31-16-235', 'domU-12-31-38-00-A4-A2', 'domU-12-31-39-02-14-35']:
            self.assertTrue(EC2.is_default(hostname))
        for hostname in ['i-672d49da', 'localhost', 'robert.redf.org']:
            self.assertFalse(EC2.is_default(hostname))
