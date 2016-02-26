# stdlib
from collections import defaultdict
from functools import partial
import logging
import time
import unittest

# 3rd
from mock import Mock, patch

# project
from tests.checks.common import Fixtures
from utils.timeout import TimeoutException


log = logging.getLogger(__name__)

WMISampler = None


def load_fixture(f, args=None):
    """
    Build a WMI query result from a file and given parameters.
    """
    properties = []
    args = args or []

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
    args = args if isinstance(args, list) else [args]
    for arg in args:
        property_name, property_value = arg
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
    # `ExecQuery` metadata
    _exec_query_call_count = Counter()
    _exec_query_run_time = 0

    def __init__(self, wmi_conn_args):
        super(SWbemServices, self).__init__()
        self._wmi_conn_args = wmi_conn_args
        self._last_wmi_query = None
        self._last_wmi_flags = None

    @classmethod
    def reset(cls):
        """
        Dirty patch to reset `SWbemServices.ExecQuery.call_count` and
        `SWbemServices._exec_query_run_time` to 0.
        """
        cls._exec_query_call_count.reset()
        cls._exec_query_run_time = 0

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
        """
        Mocked `SWbemServices.ExecQuery` method.
        """
        # Comply with `ExecQuery` metadata
        self._exec_query_call_count += 1
        time.sleep(self._exec_query_run_time)

        # Save last passed parameters
        self._last_wmi_query = query
        self._last_wmi_flags = flags

        # Mock a result
        results = []

        if query in [
                "Select AvgDiskBytesPerWrite,FreeMegabytes from Win32_PerfFormattedData_PerfDisk_LogicalDisk",  # noqa
                "Select AvgDiskBytesPerWrite,FreeMegabytes,Name from Win32_PerfFormattedData_PerfDisk_LogicalDisk"  # noqa
            ]:
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

        if query in [
                "Select NonDigit,FreeMegabytes from Win32_PerfFormattedData_PerfDisk_LogicalDisk",
                "Select FreeMegabytes,NonDigit from Win32_PerfFormattedData_PerfDisk_LogicalDisk",

            ]:  # noqa
            results += load_fixture("win32_perfformatteddata_perfdisk_logicaldisk", [("Name", "C:"), ("NonDigit", "Foo")])  # noqa

        if query == "Select IOReadBytesPerSec,IDProcess from Win32_PerfFormattedData_PerfProc_Process WHERE ( Name = 'chrome' )" \
                or query == "Select IOReadBytesPerSec,UnknownProperty from Win32_PerfFormattedData_PerfProc_Process WHERE ( Name = 'chrome' )":  # noqa
            results += load_fixture("win32_perfformatteddata_perfproc_process")

        if query == "Select IOReadBytesPerSec,ResultNotMatchingAnyTargetProperty from Win32_PerfFormattedData_PerfProc_Process WHERE ( Name = 'chrome' )":  # noqa
            results += load_fixture("win32_perfformatteddata_perfproc_process_alt")

        if query == "Select CommandLine from Win32_Process WHERE ( Handle = '4036' )" \
                or query == "Select UnknownProperty from Win32_Process WHERE ( Handle = '4036' )":
            results += load_fixture("win32_process")

        if query == ("Select ServiceUptime,TotalBytesSent,TotalBytesReceived,TotalBytesTransferred,CurrentConnections,TotalFilesSent,TotalFilesReceived,"  # noqa
                     "TotalConnectionAttemptsAllInstances,TotalGetRequests,TotalPostRequests,TotalHeadRequests,TotalPutRequests,TotalDeleteRequests,"  # noqa
                     "TotalOptionsRequests,TotalTraceRequests,TotalNotFoundErrors,TotalLockedErrors,TotalAnonymousUsers,TotalNonAnonymousUsers,TotalCGIRequests,"  # noqa
                     "TotalISAPIExtensionRequests from Win32_PerfFormattedData_W3SVC_WebService WHERE ( Name = 'Failing site' ) OR ( Name = 'Default Web Site' )"):  # noqa
            results += load_fixture("win32_perfformatteddata_w3svc_webservice", ("Name", "Default Web Site"))  # noqa

        if query == ("Select Name,State from Win32_Service WHERE ( Name = 'WSService' ) OR ( Name = 'WinHttpAutoProxySvc' )"):  # noqa
            results += load_fixture("win32_service_up", ("Name", "WinHttpAutoProxySvc"))
            results += load_fixture("win32_service_down", ("Name", "WSService"))

        if query == ("Select Message,SourceName,TimeGenerated,Type,User,InsertionStrings,EventCode from Win32_NTLogEvent WHERE ( ( SourceName = 'MSSQLSERVER' ) "  # noqa
                     "AND ( Type = 'Error' OR Type = 'Warning' ) AND TimeGenerated >= '20151224113047.000000-480' )"):  # noqa
            results += load_fixture("win32_ntlogevent")

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

def to_time(wmi_ts):
    "Just return any time struct"
    return (2015, 12, 24, 11, 30, 47, 0, 0)

def from_time(year=0, month=0, day=0, hours=0, minutes=0,
            seconds=0, microseconds=0, timezone=0):
    "Just return any WMI date"
    return "20151224113047.000000-480"

class TestCommonWMI(unittest.TestCase):
    """
    Common toolbox for WMI unit testing.
    """
    def setUp(self):
        """
        Mock WMI related Python packages, so it can be tested on any environment.
        """
        global WMISampler

        self.patcher = patch.dict('sys.modules',{
            'pywintypes': Mock(),
            'pythoncom': Mock(),
            'win32com': Mock(),
            'win32com.client': Mock(Dispatch=Dispatch),
        })
        self.patcher.start()

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
        WMISampler._wmi_connections = defaultdict(list)

    def assertWMIConn(self, wmi_sampler, param=None):
        """
        Helper, assertion on the `wmi_sampler`'s WMI connection(s):
        * `param`: parameters used to establish the connection
        """

        if param:
            connection = wmi_sampler.get_last_connection()
            wmi_conn_args, wmi_conn_kwargs = connection.get_conn_args()
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
        connection = wmi_sampler.get_last_connection()
        if query:
            last_wmi_query = connection.get_last_wmi_query()
            self.assertEquals(last_wmi_query, query)

        if flags:
            last_wmi_flags = connection.get_last_wmi_flags()
            self.assertEquals(last_wmi_flags, flags)

    def assertWMIObject(self, wmi_obj, properties):
        """
        Assert the WMI object integrity, i.e. contains the given properties.
        """
        for prop_and_value in properties:
            prop = prop_and_value[0] if isinstance(prop_and_value, tuple) else prop_and_value
            value = prop_and_value[1] if isinstance(prop_and_value, tuple) else None

            self.assertIn(prop, wmi_obj)

            if value is None:
                continue

            self.assertEquals(wmi_obj[prop], value)

    def assertWMISampler(self, wmi_sampler, properties, count=None):
        """
        Assert WMI objects' integrity among the WMI sampler.
        """
        self.assertEquals(len(wmi_sampler), count)

        for wmi_obj in wmi_sampler:
            self.assertWMIObject(wmi_obj, properties)

    def assertIn(self, first, second):
        """
        Assert `first` in `second`.

        Note: needs to be defined for Python 2.6
        """
        self.assertTrue(first in second, "{0} not in {1}".format(first, second))

    def assertNotIn(self, first, second):
        """
        Assert `first` is not in `second`.

        Note: needs to be defined for Python 2.6
        """
        self.assertTrue(first not in second, "{0} in {1}".format(first, second))

    def assertInPartial(self, first, second):
        """
        Assert `first` has a key in `second` where it's a prefix.

        Note: needs to be defined for Python 2.6
        """
        self.assertTrue(any(key for key in second if key.startswith(first)), "{0} not in {1}".format(first, second))

    def getProp(self, dict, prefix):
        """
        Get Property from dictionary `dict` starting with `prefix`.

        Note: needs to be defined for Python 2.6
        """
        for key in dict:
            if key.startswith(prefix):
                return dict[key]

        return None


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

        # Request a connection but do nothing
        with wmi_sampler.get_connection():
            pass

        # Connection was established with the right parameters
        self.assertWMIConn(wmi_sampler, param="myhost")
        self.assertWMIConn(wmi_sampler, param="some/namespace")

    def test_wmi_connection_pooling(self):
        """
        Until caching is enabled WMI connections will not be shared among WMISampler objects.
        """
        from win32com.client import Dispatch

        wmi_sampler_1 = WMISampler("Win32_PerfRawData_PerfOS_System", ["ProcessorQueueLength"])
        wmi_sampler_2 = WMISampler("Win32_OperatingSystem", ["TotalVisibleMemorySize"])
        wmi_sampler_3 = WMISampler("Win32_PerfRawData_PerfOS_System", ["ProcessorQueueLength"], host="myhost")  # noqa

        wmi_sampler_1.sample()
        wmi_sampler_2.sample()

        # one connection, two samples
        self.assertEquals(Dispatch.ConnectServer.call_count, 3, Dispatch.ConnectServer.call_count)

        wmi_sampler_3.sample()

        # two connection, three samples
        self.assertEquals(Dispatch.ConnectServer.call_count, 5, Dispatch.ConnectServer.call_count)

    def test_wql_filtering(self):
        """
        Format the filters to a comprehensive WQL `WHERE` clause.
        """
        from checks.libs.wmi import sampler
        format_filter = sampler.WMISampler._format_filter

        # Check `_format_filter` logic
        no_filters = []
        filters = [{'Name': "SomeName", 'Id': "SomeId"}]

        self.assertEquals("", format_filter(no_filters))
        self.assertEquals(" WHERE ( Name = 'SomeName' AND Id = 'SomeId' )",
                          format_filter(filters))

    def test_wql_multiquery_filtering(self):
        """
        Format the filters with multiple properties per instance to a comprehensive WQL `WHERE` clause.
        """
        from checks.libs.wmi import sampler
        format_filter = sampler.WMISampler._format_filter

        # Check `_format_filter` logic
        no_filters = []
        filters = [{'Name': "SomeName", 'Property1': "foo"}, {'Name': "OtherName", 'Property1': "bar"}]

        self.assertEquals("", format_filter(no_filters))
        self.assertEquals(" WHERE ( Property1 = 'bar' AND Name = 'OtherName' ) OR"
                          " ( Property1 = 'foo' AND Name = 'SomeName' )",
                          format_filter(filters))

    def test_wql_empty_list(self):
        """
        Format filters to a comprehensive WQL `WHERE` clause skipping empty lists.
        """

        from checks.libs.wmi import sampler
        format_filter = sampler.WMISampler._format_filter

        filters = []
        query = {}
        query['User'] = ('=', 'luser')
        query['SourceName'] = ('=', 'MSSQL')
        query['EventCode'] = []
        query['SomethingEmpty'] = []
        query['MoreNothing'] = []

        filters.append(query)

        self.assertEquals(" WHERE ( SourceName = 'MSSQL' AND User = 'luser' )",
                          format_filter(filters))

    def test_wql_filtering_op_adv(self):
        """
        Format the filters to a comprehensive WQL `WHERE` clause w/ mixed filter containing regular and operator modified properties.
        """
        from checks.libs.wmi import sampler
        format_filter = sampler.WMISampler._format_filter

        # Check `_format_filter` logic
        filters = [{'Name': "Foo%"}, {'Name': "Bar%", 'Id': ('>=', "SomeId")}, {'Name': "Zulu"}]
        self.assertEquals(" WHERE ( Name = 'Zulu' ) OR ( Name LIKE 'Bar%' AND Id >= 'SomeId' ) OR ( Name LIKE 'Foo%' )",
                          format_filter(filters))

    def test_wql_eventlog_filtering(self):
        """
        Format filters with the eventlog expected form to a comprehensive WQL `WHERE` clause.
        """

        from checks.libs.wmi import sampler
        from datetime import datetime
        from checks.wmi_check import from_time
        format_filter = sampler.WMISampler._format_filter

        filters = []
        query = {}
        and_props = ['mEssage']
        ltypes = ["Error", "Warning"]
        source_names = ["MSSQLSERVER", "IIS"]
        log_files = ["System", "Security"]
        event_codes = [302, 404, 501]
        message_filters = ["-foo", "%bar%", "%zen%"]
        last_ts = datetime(2016, 1, 1, 15, 8, 24, 78915)

        query['TimeGenerated'] = ('>=', from_time(last_ts))
        query['Type'] = ('=', 'footype')
        query['User'] = ('=', 'luser')
        query['SourceName'] = ('=', 'MSSQL')
        query['LogFile'] = ('=', 'thelogfile')

        query['Type'] = []
        for ltype in ltypes:
            query['Type'].append(('=', ltype))

        query['SourceName'] = []
        for source_name in source_names:
            query['SourceName'].append(('=', source_name))

        query['LogFile'] = []
        for log_file in log_files:
            query['LogFile'].append(('=', log_file))

        query['EventCode'] = []
        for code in event_codes:
            query['EventCode'].append(('=', code))

        query['NOT Message'] = []
        query['Message'] = []
        for filt in message_filters:
            if filt[0] == '-':
                query['NOT Message'].append(('LIKE', filt[1:]))
            else:
                query['Message'].append(('LIKE', filt))

        filters.append(query)

        self.assertEquals(" WHERE ( NOT Message LIKE 'foo' AND ( EventCode = '302' OR EventCode = '404' OR EventCode = '501' ) "
                          "AND ( SourceName = 'MSSQLSERVER' OR SourceName = 'IIS' ) AND TimeGenerated >= '2016-01-01 15:08:24.078915**********.******+' "
                          "AND User = 'luser' AND Message LIKE '%bar%' AND Message LIKE '%zen%' AND ( LogFile = 'System' OR LogFile = 'Security' ) "
                          "AND ( Type = 'Error' OR Type = 'Warning' ) )",
                          format_filter(filters, and_props))

    def test_wql_filtering_inclusive(self):
        """
        Format the filters to a comprehensive and inclusive WQL `WHERE` clause.
        """
        from checks.libs.wmi import sampler
        format_filter = sampler.WMISampler._format_filter

        # Check `_format_filter` logic
        filters = [{'Name': "SomeName"}, {'Id': "SomeId"}]
        self.assertEquals(" WHERE ( Id = 'SomeId' ) OR ( Name = 'SomeName' )",
                          format_filter(filters, True))

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
            " WHERE ( Name = 'C:' )"
        )

        # Multiple filters
        wmi_sampler = WMISampler("Win32_PerfFormattedData_PerfDisk_LogicalDisk",
                                 ["AvgDiskBytesPerWrite", "FreeMegabytes"],
                                 filters=[{'Name': "C:", 'Id': "123"}])
        wmi_sampler.sample()

        self.assertWMIQuery(
            wmi_sampler,
            "Select AvgDiskBytesPerWrite,FreeMegabytes"
            " from Win32_PerfFormattedData_PerfDisk_LogicalDisk"
            " WHERE ( Name = 'C:' AND Id = '123' )"
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

    def test_wmi_sampler_timeout(self):
        """
        Gracefully handle WMI query timeouts.
        """
        from checks.libs.wmi.sampler import WMISampler
        logger = Mock()

        # Create a sampler that timeouts
        wmi_sampler = WMISampler(logger, "Win32_PerfFormattedData_PerfDisk_LogicalDisk",
                                 ["AvgDiskBytesPerWrite", "FreeMegabytes"],
                                 timeout_duration=0.1)
        SWbemServices._exec_query_run_time = 0.11

        # `TimeoutException` exception is raised, DEBUG message logged
        self.assertRaises(TimeoutException, wmi_sampler.sample)
        self.assertTrue(wmi_sampler._sampling)
        self.assertTrue(logger.debug.called)

        # Cannot iterate on data
        self.assertRaises(TypeError, lambda: len(wmi_sampler))
        self.assertRaises(TypeError, lambda: sum(1 for _ in wmi_sampler))

        # Recover from timeout at next iteration
        wmi_sampler.sample()
        self.assertFalse(wmi_sampler._sampling)

        # The existing query was retrieved
        self.assertEquals(SWbemServices.ExecQuery.call_count, 1, SWbemServices.ExecQuery.call_count)

        # Data is populated
        self.assertEquals(len(wmi_sampler), 2)
        self.assertEquals(sum(1 for _ in wmi_sampler), 2)

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

        self.assertWMISampler(
            wmi_raw_sampler,
            [
                ("CounterRawCount", 500), ("CounterCounter", 50),
                "Timestamp_Sys100NS", "Frequency_Sys100NS", "name"
            ],
            count=2
        )

    def test_raw_properties_fallback(self):
        """
        Print a warning on RAW Performance classes if the calculator is undefined.

        Returns the original RAW value.
        """
        from checks.libs.wmi.sampler import WMISampler
        logger = Mock()
        wmi_raw_sampler = WMISampler(logger, "Win32_PerfRawData_PerfOS_System", ["UnknownCounter", "MissingProperty"])  # noqa
        wmi_raw_sampler.sample()

        self.assertWMISampler(
            wmi_raw_sampler,
            [
                ("UnknownCounter", 999), "Timestamp_Sys100NS", "Frequency_Sys100NS", "Name"
            ],
            count=1
        )

        self.assertTrue(logger.warning.called)

    def test_missing_property(self):
        """
        Do not raise on missing properties but backfill with empty values.
        """
        wmi_raw_sampler = WMISampler("Win32_PerfRawData_PerfOS_System", ["UnknownCounter", "MissingProperty"])  # noqa
        wmi_raw_sampler.sample()

        self.assertWMISampler(wmi_raw_sampler, ["MissingProperty"], count=1)


class TestIntegrationWMI(unittest.TestCase):
    """
    Integration tests for WMISampler.
    """
    pass
