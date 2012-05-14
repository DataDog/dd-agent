import unittest
import logging
import types
import time

from checks.ec2 import EC2

class TestEC2(unittest.TestCase):
    def setUp(self):
        self._ec2 = EC2(logging.getLogger("tests"))

    def test_metadata(self):
        start = time.time()
        d = self._ec2.get_metadata()
        end = time.time()
        assert type(d) == types.DictType
        # Either we're on ec2 or we're not (7 attributes expected)
        assert len(d) == 0 or len(d) >= 7
        if len(d) > 0:
            assert "hostname" in d
            assert "instance-id" in d
        # either way, it should have not taken more than 1s to get an answer
        assert end - start <= 1.0, "It took %s seconds to get ec2 metadata" % (end-start)

if __name__ == "__main__":
    unittest.main()
