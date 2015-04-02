# stdlib
import os
import unittest

# project
from utils.process import pid_exists


class UtilsProcessTest(unittest.TestCase):
    def test_my_own_pid(self):
        my_pid = os.getpid()
        self.assertTrue(pid_exists(my_pid))

    def test_inexistant_pid(self):
        # There will be one point where we finally find a free PID
        for pid in xrange(30000):
            if not pid_exists(pid):
                return
        raise Exception("Probably a bug in pid_exists or more than 30000 procs!!")
