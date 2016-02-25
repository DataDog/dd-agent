# stdlib
import unittest

# datadog
from checks.libs.wmi.counter_type import calculator, get_calculator, UndefinedCalculator


class TestWMICalculators(unittest.TestCase):
    """
    Unit testing for WMI calculators.
    """
    def setUp(self):
        """
        Defines two WMI object samples.
        """
        self.previous = {
            'WMIPropertyName': 300,
            'Timestamp_Sys100NS': 50,
        }

        self.current = {
            'WMIPropertyName': 500,
            'Timestamp_Sys100NS': 52,
            'Frequency_Sys100NS': 0.5,
        }

    def assertPropertyValue(self, counter_type, value):
        """
        Handler to assert the value returned by the counter_type's calculator on the given sample.
        """
        calculator = get_calculator(counter_type)
        self.assertEquals(value, calculator(self.previous, self.current, "WMIPropertyName"))

    def test_calculator_decorator(self):
        """
        Asssign a calculator to a counter_type. Raise when the calculator is missing.
        """
        @calculator(123456)
        def do_something(*args, **kwargs):
            """A function that does something."""
            pass

        self.assertEquals("do_something", do_something.__name__)
        self.assertEquals("A function that does something.", do_something.__doc__)

        self.assertTrue(get_calculator(123456))

        self.assertRaises(UndefinedCalculator, get_calculator, 654321)

    def test_calculator_values(self):
        """
        Check the computed values from calculators.
        """
        # PERF_COUNTER_RAWCOUNT
        self.assertPropertyValue(65536, 500)

        # PERF_COUNTER_LARGE_RAWCOUNT
        self.assertPropertyValue(65792, 500)

        # PERF_100NSEC_TIMER
        self.assertPropertyValue(542180608, 10000)

        # PERF_COUNTER_BULK_COUNT
        self.assertPropertyValue(272696576, 50)

        # PERF_COUNTER_COUNTER
        self.assertPropertyValue(272696320, 50)
