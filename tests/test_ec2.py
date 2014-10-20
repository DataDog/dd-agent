import unittest
import os
import types
import time

from util import EC2

class TestEC2(unittest.TestCase):

    def test_metadata(self):
        # Skip this step on travis
        if os.environ.get('TRAVIS', False): return
        # Test gathering metadata from ec2
        start = time.time()
        d = EC2.get_metadata({'collect_instance_metadata': True})
        end = time.time()
        assert type(d) == types.DictType
        # Either we're on ec2 or we're not (at least 7 attributes expected)
        assert len(d) == 0 or len(d) >= 7, d
        if "instance-id" in d:
            assert d["instance-id"].startswith("i-"), d
            assert d["hostname"].startswith("i-") or d["hostname"].startswith("domU-"), d
        assert end - start <= 1.1, "It took %s seconds to get ec2 metadata" % (end-start)

if __name__ == "__main__":
    unittest.main()
