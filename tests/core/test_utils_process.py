# stdlib
import os
import unittest

# project
from utils.process import is_my_process, pid_exists
from utils.platform import Platform


class UtilsProcessTest(unittest.TestCase):
    def test_my_own_pid(self):
        my_pid = os.getpid()
        self.assertTrue(pid_exists(my_pid))
        if not Platform.is_windows():
            '''Test is currently not valid under windows, because
               of the way nosetests is implemented.  The command
               is 'runpy.py', but the executable command line is
               ['d:\\devtools\\python27\\python.exe', 'D:\\devtools\\python27\\Scripts\\nosetests.exe', 'tests.core']
               Removing until we can make an more accurate test
               '''
            self.assertTrue(is_my_process(my_pid))

    def test_inexistant_pid(self):
        # There will be one point where we finally find a free PID
        for pid in xrange(30000):
            if not pid_exists(pid):
                return
        raise Exception("Probably a bug in pid_exists or more than 30000 procs!!")

    def test_existing_process(self):
        self.assertFalse(is_my_process(1))
