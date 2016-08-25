# stdlib
import unittest

# datadog
from checks.libs.wmi.exceptions import com_error, raise_on_com_error


class MockedWMICOMError(Exception):
    """
    Mocking a WMI `com_error` error.
    """
    def __init__(self, error_id):
        super(MockedWMICOMError, self).__init__()
        self.error_id = error_id

    def __getitem__(self, index):
        if index == 0:
            return self.error_id

        raise NotImplementedError


class TestWMIExceptions(unittest.TestCase):
    """
    Unit testing for WMI `com_error` errors and user exceptions.
    """
    def test_register_com_error(self):
        """
        `com_error` decorator register and map a WMI `com_error` to an user exception.
        """
        # Mock a WMI `com_error`
        sample_error = MockedWMICOMError(123456)

        # Map it to an user exception
        @com_error(sample_error.error_id)
        class WMISampleException(Exception):
            """
            Sample WMI exception.
            """
            pass

        # Assert that the exception is raised
        with self.assertRaises(WMISampleException):
            raise_on_com_error(sample_error)

    def test_unregistred_com_error(self):
        """
        Unknown `com_error` errors remain intact.
        """
        # Mock a WMI `com_error`, do not register it
        sample_error = MockedWMICOMError(456789)

        # Assert that the original exception is raised
        with self.assertRaises(MockedWMICOMError):
            raise_on_com_error(sample_error)
