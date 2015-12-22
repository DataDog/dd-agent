# stdlib
from functools import partial
import logging
import unittest

# 3rd
from mock import Mock

# project
from tests.checks.common import Fixtures


log = logging.getLogger(__name__)

WMISampler = None


# Thoughts
# Log WMI activity
# Mechanism to timeout
# Check when pywintypes.com_error are raised
# Check the role of the flags


def load_fixture(f, args=None):
    """
    Build a WMI query result from a file and given parameters.
    """
    properties = []

    def extract_line(line):
        """
        Extract a property name, value and the qualifiers from a fixture line.

        Return (property name, property value, property qualifiers)
        """
        property_counter_type = ""

        try:
            property_name, property_value, property_counter_type = line.split(" ")
        except ValueError:
            property_name, property_value = line.split(" ")

        property_qualifiers = [Mock(Name='CounterType', Value=int(property_counter_type))] \
            if property_counter_type else []

        return property_name, property_value, property_qualifiers

    # Build from file
    data = Fixtures.read_file(f)
    for l in data.splitlines():
        property_name, property_value, property_qualifiers = extract_line(l)
        properties.append(
            Mock(Name=property_name, Value=property_value, Qualifiers_=property_qualifiers)
        )

    # Append extra information
    if args:
        property_name, property_value = args
        properties.append(Mock(Name=property_name, Value=property_value, Qualifiers_=[]))

    return [Mock(Properties_=properties)]


class Counter(object):
    def __init__(self):
        self.value = 0

    def __iadd__(self, other):
        self.value += other
        return self

    def __eq__(self, other):
        return self.value == other

    def __str__(self):
        return str(self.value)

    def reset(self):
        self.value = 0


class SWbemServices(object):
    """
    SWbemServices a.k.a. (mocked) WMI connection.
    Save connection parameters so it can be tested.
    """
    _exec_query_call_count = Counter()

    def __init__(self, wmi_conn_args):
        super(SWbemServices, self).__init__()
        self._wmi_conn_args = wmi_conn_args
        self._last_wmi_query = None
        self._last_wmi_flags = None

    @classmethod
    def reset(cls):
        """
        FIXME - Dirty patch to reset `SWbemServices.ExecQuery` to 0.
        """
        cls._exec_query_call_count.reset()

    def get_conn_args(self):
        """
        Return parameters used to set up the WMI connection.
        """
        return self._wmi_conn_args

    def get_last_wmi_query(self):
        """
        Return the last WMI query submitted via the WMI connection.
        """
        return self._last_wmi_query

    def get_last_wmi_flags(self):
        """
        Return the last WMI flags submitted via the WMI connection.
        """
        return self._last_wmi_flags

    def ExecQuery(self, query, query_language, flags):
        SWbemServices._exec_query_call_count += 1
        self._last_wmi_query = query
        self._last_wmi_flags = flags
        results = []

        if query == "Select AvgDiskBytesPerWrite,FreeMegabytes from Win32_PerfFormattedData_PerfDisk_LogicalDisk":  # noqa
            results += load_fixture("win32_perfformatteddata_perfdisk_logicaldisk", ("Name", "C:"))
            results += load_fixture("win32_perfformatteddata_perfdisk_logicaldisk", ("Name", "D:"))

        if query == "Select CounterRawCount,CounterCounter,Timestamp_Sys100NS,Frequency_Sys100NS from Win32_PerfRawData_PerfOS_System":  # noqa
            # Mock a previous and a current sample
            sample_file = "win32_perfrawdata_perfos_system_previous" if flags == 131120\
                else "win32_perfrawdata_perfos_system_current"
            results += load_fixture(sample_file, ("Name", "C:"))
            results += load_fixture(sample_file, ("Name", "D:"))

        if query == "Select UnknownCounter,MissingProperty,Timestamp_Sys100NS,Frequency_Sys100NS from Win32_PerfRawData_PerfOS_System":  # noqa
            results += load_fixture("win32_perfrawdata_perfos_system_unknown", ("Name", "C:"))
            results += load_fixture("win32_perfrawdata_perfos_system_unknown", ("Name", "D:"))

        if query == "Select IOReadBytesPerSec,IDProcess from Win32_PerfFormattedData_PerfProc_Process WHERE Name = 'chrome'" \
                or query == "Select IOReadBytesPerSec,UnknownProperty from Win32_PerfFormattedData_PerfProc_Process WHERE Name = 'chrome'":  # noqa
            results += load_fixture("win32_perfformatteddata_perfproc_process")

        if query == "Select IOReadBytesPerSec,ResultNotMatchingAnyTargetProperty from Win32_PerfFormattedData_PerfProc_Process WHERE Name = 'chrome'":  # noqa
            results += load_fixture("win32_perfformatteddata_perfproc_process_alt")

        if query == "Select CommandLine from Win32_Process WHERE Handle = '4036'" \
                or query == "Select UnknownProperty from Win32_Process WHERE Handle = '4036'":
            results += load_fixture("win32_process")

        return results

    ExecQuery.call_count = _exec_query_call_count


class Dispatch(object):
    """
    Mock for win32com.client Dispatch class.
    """
    _connect_call_count = Counter()

    def __init__(self, *args, **kwargs):
        pass

    @classmethod
    def reset(cls):
        """
        FIXME - Dirty patch to reset `ConnectServer.call_count` to 0.
        """
        cls._connect_call_count.reset()

    def ConnectServer(self, *args, **kwargs):
        """
        Return a WMI connection, a.k.a. a SWbemServices object.
        """
        Dispatch._connect_call_count += 1
        wmi_conn_args = (args, kwargs)
        return SWbemServices(wmi_conn_args)

    ConnectServer.call_count = _connect_call_count


class TestCommonWMI(unittest.TestCase):
    """
    Common toolbox for WMI unit testing.
    """
    def setUp(self):
        """
        Mock WMI related Python packages, so it can be tested on any environment.
        """
        import sys
        global WMISampler

        sys.modules['pywintypes'] = Mock()
        sys.modules['win32com'] = Mock()
        sys.modules['win32com.client'] = Mock(Dispatch=Dispatch)

        from checks.libs.wmi import sampler
        WMISampler = partial(sampler.WMISampler, log)

    def tearDown(self):
        """
        Reset Mock counters, flush samplers and connections
        """
        # Reset counters
        Dispatch.reset()
        SWbemServices.reset()

        # Flush cache
        from checks.libs.wmi.sampler import WMISampler
        WMISampler._wmi_locators = {}
        WMISampler._wmi_connections = {}

    def assertWMIConnWith(self, wmi_sampler, param):
        """
        Helper, assert that the WMI connection was established with the right parameter and value.
        """
        wmi_instance = wmi_sampler._get_connection()
        wmi_conn_args, wmi_conn_kwargs = wmi_instance.get_conn_args()
        if isinstance(param, tuple):
            key, value = param
            self.assertIn(key, wmi_conn_kwargs)
            self.assertEquals(wmi_conn_kwargs[key], value)
        else:
            self.assertIn(param, wmi_conn_args)

    def assertWMIQuery(self, wmi_sampler, query=None, flags=None):
        """
        Helper, assert that the given WMI query and flags were submitted.
        """
        wmi_instance = wmi_sampler._get_connection()

        if query:
            last_wmi_query = wmi_instance.get_last_wmi_query()
            self.assertEquals(last_wmi_query, query)

        if flags:
            last_wmi_flags = wmi_instance.get_last_wmi_flags()
            self.assertEquals(last_wmi_flags, flags)

    def assertWMIObject(self, wmi_obj, property_names):
        """
        Assert the WMI object integrity.
        """
        for prop in property_names:
            self.assertIn(prop, wmi_obj)

    def assertIn(self, first, second):
        """
        Assert `first` in `second`.

        Note: needs to be defined for Python 2.6
        """
        self.assertTrue(first in second, "{0} not in {1}".format(first, second))


class TestUnitWMISampler(TestCommonWMI):
    """
    Unit tests for WMISampler.
    """
    def test_wmi_connection(self):
        """
        Establish a WMI connection to the specified host/namespace, with the right credentials.
        """
        wmi_sampler = WMISampler(
            "Win32_PerfRawData_PerfOS_System",
            ["ProcessorQueueLength"],
            host="myhost",
            namespace="some/namespace",
            username="datadog",
            password="password"
        )
        wmi_conn = wmi_sampler._get_connection()

        # WMI connection is cached
        self.assertIn('myhost:some/namespace:datadog', wmi_sampler._wmi_connections)

        # Connection was established with the right parameters
        self.assertWMIConnWith(wmi_sampler, "myhost")
        self.assertWMIConnWith(wmi_sampler, "some/namespace")

    def test_wmi_connection_pooling(self):
        """
        Share WMI connections among WMISampler objects.
        """
        from win32com.client import Dispatch

        wmi_sampler_1 = WMISampler("Win32_PerfRawData_PerfOS_System", ["ProcessorQueueLength"])
        wmi_sampler_2 = WMISampler("Win32_OperatingSystem", ["TotalVisibleMemorySize"])
        wmi_sampler_3 = WMISampler("Win32_PerfRawData_PerfOS_System", ["ProcessorQueueLength"], host="myhost")  # noqa

        wmi_sampler_1.sample()
        wmi_sampler_2.sample()

        self.assertEquals(Dispatch.ConnectServer.call_count, 1, Dispatch.ConnectServer.call_count)

        wmi_sampler_3.sample()

        self.assertEquals(Dispatch.ConnectServer.call_count, 2, Dispatch.ConnectServer.call_count)

    def test_wql_filtering(self):
        """
        Format the filters to a comprehensive WQL `WHERE` clause.
        """
        from checks.libs.wmi import sampler
        format_filter = sampler.WMISampler._format_filter

        # Check `_format_filter` logic
        no_filters = []
        filters = [{'Name': "SomeName"}, {'Id': "SomeId"}]

        self.assertEquals("", format_filter(no_filters))
        self.assertEquals(" WHERE Id = 'SomeId' AND Name = 'SomeName'",
                          format_filter(filters))

    def test_wmi_query(self):
        """
        Query WMI using WMI Query Language (WQL).
        """
        # No filters
        wmi_sampler = WMISampler("Win32_PerfFormattedData_PerfDisk_LogicalDisk",
                                 ["AvgDiskBytesPerWrite", "FreeMegabytes"])
        wmi_sampler.sample()

        self.assertWMIQuery(
            wmi_sampler,
            "Select AvgDiskBytesPerWrite,FreeMegabytes"
            " from Win32_PerfFormattedData_PerfDisk_LogicalDisk"
        )

        # Single filter
        wmi_sampler = WMISampler("Win32_PerfFormattedData_PerfDisk_LogicalDisk",
                                 ["AvgDiskBytesPerWrite", "FreeMegabytes"],
                                 filters=[{'Name': "C:"}])
        wmi_sampler.sample()

        self.assertWMIQuery(
            wmi_sampler,
            "Select AvgDiskBytesPerWrite,FreeMegabytes"
            " from Win32_PerfFormattedData_PerfDisk_LogicalDisk"
            " WHERE Name = 'C:'"
        )

        # Multiple filters
        wmi_sampler = WMISampler("Win32_PerfFormattedData_PerfDisk_LogicalDisk",
                                 ["AvgDiskBytesPerWrite", "FreeMegabytes"],
                                 filters=[{'Name': "C:"}, {'Id': "123"}])
        wmi_sampler.sample()

        self.assertWMIQuery(
            wmi_sampler,
            "Select AvgDiskBytesPerWrite,FreeMegabytes"
            " from Win32_PerfFormattedData_PerfDisk_LogicalDisk"
            " WHERE Id = '123' AND Name = 'C:'"
        )

    def test_wmi_parser(self):
        """
        Parse WMI objects from WMI query results.
        """
        wmi_sampler = WMISampler("Win32_PerfFormattedData_PerfDisk_LogicalDisk",
                                 ["AvgDiskBytesPerWrite", "FreeMegabytes"])
        wmi_sampler.sample()

        # Assert `results`
        expected_results = [
            {
                'freemegabytes': 19742.0,
                'name': 'C:',
                'avgdiskbytesperwrite': 1536.0
            }, {
                'freemegabytes': 19742.0,
                'name': 'D:',
                'avgdiskbytesperwrite': 1536.0
            }
        ]

        self.assertEquals(wmi_sampler, expected_results, wmi_sampler)

    def test_wmi_sampler_iterator_getter(self):
        """
        Iterate/Get on the WMISampler object iterates/gets on its current sample.
        """
        wmi_sampler = WMISampler("Win32_PerfFormattedData_PerfDisk_LogicalDisk",
                                 ["AvgDiskBytesPerWrite", "FreeMegabytes"])
        wmi_sampler.sample()

        self.assertEquals(len(wmi_sampler), 2)

        # Using an iterator
        for wmi_obj in wmi_sampler:
            self.assertWMIObject(wmi_obj, ["AvgDiskBytesPerWrite", "FreeMegabytes", "name"])

        # Using an accessor
        for index in xrange(0, 2):
            self.assertWMIObject(wmi_sampler[index], ["AvgDiskBytesPerWrite", "FreeMegabytes", "name"])

    def test_raw_perf_properties(self):
        """
        Extend the list of properties to query for RAW Performance classes.
        """
        # Formatted Performance class
        wmi_sampler = WMISampler("Win32_PerfFormattedData_PerfOS_System", ["ProcessorQueueLength"])
        self.assertEquals(len(wmi_sampler.property_names), 1)

        # Raw Performance class
        wmi_sampler = WMISampler("Win32_PerfRawData_PerfOS_System", ["CounterRawCount", "CounterCounter"])  # noqa
        self.assertEquals(len(wmi_sampler.property_names), 4)

    def test_raw_initial_sampling(self):
        """
        Query for initial sample for RAW Performance classes.
        """
        wmi_sampler = WMISampler("Win32_PerfRawData_PerfOS_System", ["CounterRawCount", "CounterCounter"])  # noqa
        wmi_sampler.sample()

        # 2 queries should have been made: one for initialization, one for sampling
        self.assertEquals(SWbemServices.ExecQuery.call_count, 2, SWbemServices.ExecQuery.call_count)

        # Repeat
        wmi_sampler.sample()
        self.assertEquals(SWbemServices.ExecQuery.call_count, 3, SWbemServices.ExecQuery.call_count)

    def test_raw_cache_qualifiers(self):
        """
        Cache the qualifiers on the first query against RAW Performance classes.
        """
        # Append `flag_use_amended_qualifiers` flag on the first query
        wmi_raw_sampler = WMISampler("Win32_PerfRawData_PerfOS_System", ["CounterRawCount", "CounterCounter"])  # noqa
        wmi_raw_sampler._query()

        self.assertWMIQuery(wmi_raw_sampler, flags=131120)

        wmi_raw_sampler._query()
        self.assertWMIQuery(wmi_raw_sampler, flags=48)

        # Qualifiers are cached
        self.assertTrue(wmi_raw_sampler.property_counter_types)
        self.assertIn('CounterRawCount', wmi_raw_sampler.property_counter_types)
        self.assertIn('CounterCounter', wmi_raw_sampler.property_counter_types)

    def test_raw_properties_formatting(self):
        """
        WMI Object's RAW data are returned formatted.
        """
        wmi_raw_sampler = WMISampler("Win32_PerfRawData_PerfOS_System", ["CounterRawCount", "CounterCounter"])  # noqa
        wmi_raw_sampler.sample()

        self.assertEquals(len(wmi_raw_sampler), 2)

        # Using an iterator
        for wmi_obj in wmi_raw_sampler:
            self.assertWMIObject(wmi_obj, ["CounterRawCount", "CounterCounter", "Timestamp_Sys100NS", "Frequency_Sys100NS", "name"])  # noqa
            self.assertEquals(wmi_obj['CounterRawCount'], 500)
            self.assertEquals(wmi_obj['CounterCounter'], 50)

        # Using an accessor
        for index in xrange(0, 2):
            self.assertWMIObject(wmi_raw_sampler[index], ["CounterRawCount", "CounterCounter", "Timestamp_Sys100NS", "Frequency_Sys100NS", "name"])  # noqa
            self.assertEquals(wmi_raw_sampler[index]['CounterRawCount'], 500)
            self.assertEquals(wmi_raw_sampler[index]['CounterCounter'], 50)

    def test_raw_properties_fallback(self):
        """
        Print a warning on RAW Performance classes if the calculator is undefined.

        Returns the original RAW value.
        """
        from checks.libs.wmi.sampler import WMISampler
        logger = Mock()
        wmi_raw_sampler = WMISampler(logger, "Win32_PerfRawData_PerfOS_System", ["UnknownCounter", "MissingProperty"])  # noqa
        wmi_raw_sampler.sample()

        self.assertEquals(len(wmi_raw_sampler), 2)

        for wmi_obj in wmi_raw_sampler:
            self.assertWMIObject(wmi_obj, ["UnknownCounter", "Timestamp_Sys100NS", "Frequency_Sys100NS", "name"])  # noqa
            self.assertEquals(wmi_obj['UnknownCounter'], 999)

        self.assertTrue(logger.warning.called)

    def test_missing_property(self):
        """
        Do not raise on missing properties.
        """
        wmi_raw_sampler = WMISampler("Win32_PerfRawData_PerfOS_System", ["UnknownCounter", "MissingProperty"])  # noqa
        wmi_raw_sampler.sample()

        self.assertEquals(len(wmi_raw_sampler), 2)

        for wmi_obj in wmi_raw_sampler:
            # Access a non existent property
            self.assertFalse(wmi_obj['MissingProperty'])


class TestIntegrationWMI(unittest.TestCase):
    """
    Integration tests for WMISampler.
    """
    pass
