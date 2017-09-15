# provided for backward compatibility.  wmi_check.py renamed to winwmi_check.py
# to prevent collision with the actual wmi check; provide the redirect for
# any agent check that uses the base library
#
# this file will be deprecated in Agent6
from checks.winwmi_check import (  # noqa: F401
    WMIMetric,
    InvalidWMIQuery,
    MissingTagBy,
    TagQueryUniquenessFailure,
    WinWMICheck,
    to_time,
    from_time,
) # noqa: F401
