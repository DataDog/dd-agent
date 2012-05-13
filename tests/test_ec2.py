import unittest
import logging
import types

from checks.ec2 import EC2

class TestEC2(unittest.TestCase):
    def setUp(self):
        self._ec2 = EC2(logging.getLogger("tests"))

    def test_metadata(self):
        d = self._ec2.get_metadata()
        assert type(d) == types.DictType
        # Either we're on ec2 or we're not (7 attributes expected)
        assert len(d) == 0 or len(d) >= 7
        if len(d) > 0:
            assert "hostname" in d
            assert "instance-id" in d

if __name__ == "__main__":
    unittest.main()
