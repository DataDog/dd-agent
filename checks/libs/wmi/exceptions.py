"""
List WMI "known" `com_errors` errors.

Translate to user intelligible exceptions.
"""

_user_exception_by_com_errors = {}


def com_error(error_id):
    """
    A decorator that assigns an `error_id` to an intelligible exception.
    """
    def set_exception(exception):
        _user_exception_by_com_errors[error_id] = exception
        return exception
    return set_exception


def raise_on_com_error(error):
    """
    Raise the user exception associated with the given `com_error` or
    fall back to the original exception.
    """
    raise _user_exception_by_com_errors.get(error[0], error)


# List of user exceptions
class WMIException(Exception):
    """
    Abtract exception for WMI.
    """
    def __init__(self):
        """
        Use the class docstring as an exception message.
        """
        super(WMIException, self).__init__(self.__doc__)


@com_error(-2147217392)
class WMIInvalidClass(WMIException):
    """WMI class is invalid."""
    pass
