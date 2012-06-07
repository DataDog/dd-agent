import unittest
import logging
import types
import time

from checks.ec2 import EC2

class TestEC2(unittest.TestCase):
    def setUp(self):
        self._ec2 = EC2(logging.getLogger("tests"))

    def test_metadata(self):
        # Test gathering metadata from ec2
        start = time.time()
        d = self._ec2.get_metadata()
        end = time.time()
        assert type(d) == types.DictType
        # fqdn must be set on ec2 and elsewhere
        assert "hostname" in d, d
        assert "fqdn" in d
        if d["fqdn"] != "localhost": # travis-ci
            assert d["fqdn"].startswith(d["hostname"]), d
        # Either we're on ec2 or we're not (at least 7 attributes expected)
        assert len(d) == 2 or len(d) >= 7, d
        if len(d) > 2:
            assert "instance-id" in d, d
            assert d["instance-id"].startswith("i-"), d
            assert d["hostname"].startswith("i-") or d["hostname"].startswith("domU-"), d
        assert end - start <= 1.1, "It took %s seconds to get ec2 metadata" % (end-start)

if __name__ == "__main__":
    unittest.main()
