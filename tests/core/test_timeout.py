# stdlib
import unittest
import time

# datadog
from utils.timeout import _thread_by_func, timeout, TimeoutException

count = 0


class SomeException(Exception):
    """A generic exception"""


@timeout(0.2)
def make_sum(a, b, sleep=0, raise_exception=False):
    """Sleep, sum and return `a` with `b`"""
    global count
    count += 1
    time.sleep(sleep)
    if raise_exception:
        raise SomeException()
    return a + b


class MyClass(object):
    """
    A simple class example.
    """
    def __init__(self):
        """
        Decorate `make_sum`.
        """
        self.make_sum = timeout(0.2)(self.make_sum)

    def make_sum(self, a, b, sleep=0, raise_exception=False): # pylint: disable=E0202
        """Sleep, sum and return `a` with `b`"""
        global count
        count += 1
        time.sleep(sleep)


class TestTimeout(unittest.TestCase):
    """
    Test timeout decorator logic.
    """

    def setUp(self):
        global count
        count = 0

    def tearDown(self):
        """
        Wait for all threads to end to avoid contamination between each tests.
        """
        for key, worker in _thread_by_func.iteritems():
            while worker.is_alive():
                time.sleep(0.2)
        for key in _thread_by_func.keys():
            del _thread_by_func[key]

    def test_preserve(self):
        """
        Preserve function name and docstring.
        """
        self.assertEquals(make_sum.__name__, "make_sum")
        self.assertEquals(make_sum.__doc__, "Sleep, sum and return `a` with `b`")

    def test_no_timeout(self):
        """
        Return the result when the method runtime does not exceed the limit set.
        """
        self.assertEquals(make_sum(1, 2), 3)

    def test_exception_propagation(self):
        """
        Propagate exceptions.
        """
        self.assertRaises(SomeException, make_sum, 1, 2, raise_exception=True)

    def test_raise_on_timeout(self):
        """
        Raise `TimeoutException` on timeouts.
        """
        self.assertRaises(TimeoutException, make_sum, 1, 2, sleep=0.5)

    def test_refetch_thread(self):
        """
        Refetch an existing thread when it exists.
        """
        #  This should create a thread
        self.assertRaises(TimeoutException, make_sum, 1, 2, sleep=0.5)
        self.assertEquals(count, 1)

        time.sleep(0.5)

        # This should refetch the existing thread
        self.assertEquals(make_sum(1, 2, sleep=0.5), 3)
        self.assertEquals(count, 1)

        # This should create a new thread
        self.assertRaises(TimeoutException, make_sum, 1, 2, sleep=0.5)
        self.assertEquals(count, 2)

    def test_multiple_threads(self):
        """
        Create one thread per function call.
        """
        # Create one thread
        self.assertRaises(TimeoutException, make_sum, 1, 2, sleep=0.5)

        #  ... and a second one
        self.assertRaises(TimeoutException, make_sum, 2, 3, sleep=0.5)

        self.assertEquals(count, 2)

    def test_multiple_instances(self):
        """
        Same method within different instances = different threads
        """
        # Create one thread
        self.assertRaises(TimeoutException, MyClass().make_sum, 1, 2, sleep=0.5)

        # Different instance = new thread
        self.assertRaises(TimeoutException, MyClass().make_sum, 1, 2, sleep=0.5)
        self.assertEquals(count, 2)
