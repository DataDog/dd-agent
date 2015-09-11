# 3rd
from mock import Mock

# project
from tests.checks.common import AgentCheckTest, Fixtures


def load_fixture(f, args):
    """
    Build a WMI query result from a file and given parameters.
    """
    properties = []

    # Build from file
    data = Fixtures.read_file(f)
    for l in data.splitlines():
        property_name, property_value = l.split(" ")
        properties.append(Mock(Name=property_name, Value=property_value))

    # Append extra information
    property_name, property_value = args
    properties.append(Mock(Name=property_name, Value=property_value))

    return [Mock(Properties_=properties)]


class MockWMIConnection(object):
    """
    Mocked WMI connection.
    Save connection parameters so it can be tested.
    """
    def __init__(self, wmi_conn_args):
        super(MockWMIConnection, self).__init__()
        self._wmi_conn_args = wmi_conn_args

    def get_conn_args(self):
        """
        Return parameters used to set up the WMI connection.
        """
        return self._wmi_conn_args

    def ExecQuery(self, wql):
        if wql == "Select AvgDiskBytesPerWrite,FreeMegabytes "\
                  "from Win32_PerfFormattedData_PerfDisk_LogicalDisk":
            results = load_fixture("win32_perfformatteddata_perfdisk_logicaldisk", ("Name", "C:"))
            results += load_fixture("win32_perfformatteddata_perfdisk_logicaldisk", ("Name", "D:"))
            return results

        return []


class MockDispatch(object):
    """
    Mock for win32com.client Dispatch class.
    """
    def __init__(self, *args, **kwargs):
        pass

    def ConnectServer(self, *args, **kwargs):
        """
        Return a MockWMIConnection
        """
        wmi_conn_args = (args, kwargs)
        return MockWMIConnection(wmi_conn_args)


class WMITestCase(AgentCheckTest):
    CHECK_NAME = 'wmi_alternative_check'

    WMI_CONNECTION_CONFIG = {
        'host': "myhost",
        'namespace': "some/namespace",
        'username': "datadog",
        'password': "datadog",
        'class': "Win32_OperatingSystem",
        'metrics': [["NumberOfProcesses", "system.proc.count", "gauge"],
                    ["NumberOfUsers", "system.users.count", "gauge"]]
    }

    WMI_CONFIG = {
        'class': "Win32_PerfFormattedData_PerfDisk_LogicalDisk",
        'metrics': [["AvgDiskBytesPerWrite", "winsys.disk.avgdiskbytesperwrite", "gauge"],
                    ["FreeMegabytes", "winsys.disk.freemegabytes", "gauge"]],
        'tag_by': "Name"
    }

    WMI_CONFIG_NO_TAG_BY = {
        'class': "Win32_PerfFormattedData_PerfDisk_LogicalDisk",
        'metrics': [["AvgDiskBytesPerWrite", "winsys.disk.avgdiskbytesperwrite", "gauge"],
                    ["FreeMegabytes", "winsys.disk.freemegabytes", "gauge"]],
    }

    WMI_CONFIG_FILTER = {
        'class': "Win32_PerfFormattedData_PerfDisk_LogicalDisk",
        'metrics': [["AvgDiskBytesPerWrite", "winsys.disk.avgdiskbytesperwrite", "gauge"],
                    ["FreeMegabytes", "winsys.disk.freemegabytes", "gauge"]],
        'filters': [{'Name': "C:"}]
    }

    def setUp(self):
        """
        Mock WMI related Python packages, so it can be tested on any environment.
        """
        import sys
        sys.modules['pywintypes'] = Mock()
        sys.modules['win32com'] = Mock()
        sys.modules['win32com.client'] = Mock(Dispatch=MockDispatch)

    def assertWMIConnWith(self, wmi_instance, param):
        """
        Helper, assert that the WMI connection was established with the right parameter and value.
        """
        wmi_conn_args, wmi_conn_kwargs = wmi_instance.get_conn_args()
        if isinstance(param, tuple):
            key, value = param
            self.assertIn(key, wmi_conn_kwargs)
            self.assertEquals(wmi_conn_kwargs[key], value)
        else:
            self.assertIn(param, wmi_conn_args)

    def test_wmi_connection(self):
        """
        Establish a WMI connection to the specified host/namespace, with the right credentials.
        """
        # Run check
        config = {
            'instances': [self.WMI_CONNECTION_CONFIG]
        }
        self.run_check(config)

        # WMI connection is cached
        self.assertIn('myhost:some/namespace:datadog:datadog', self.check.wmi_conns)
        wmi_conn = self.check.wmi_conns['myhost:some/namespace:datadog:datadog']

        # Connection was established with the right parameters
        self.assertWMIConnWith(wmi_conn, "myhost")
        self.assertWMIConnWith(wmi_conn, "some/namespace")

    def test_wmi_properties(self):
        """
        Compute a (metric name, metric type) by WMI property map and a property list.
        """
        # Set up the check
        config = {
            'instances': [self.WMI_CONNECTION_CONFIG]
        }
        self.run_check(config)

        # WMI props are cached
        self.assertIn('myhost:some/namespace:Win32_OperatingSystem', self.check.wmi_props)
        metric_name_and_type_by_property, properties = \
            self.check.wmi_props['myhost:some/namespace:Win32_OperatingSystem']

        # Assess
        self.assertEquals(
            metric_name_and_type_by_property,
            {
                'numberofprocesses': ("system.proc.count", "gauge"),
                'numberofusers': ("system.users.count", "gauge")
            }
        )
        self.assertEquals(properties, ["NumberOfProcesses", "NumberOfUsers"])

    def test_metric_extraction(self):
        """
        Extract metrics from WMI query results.
        """
        # Set up the check
        config = {
            'instances': [self.WMI_CONNECTION_CONFIG]
        }
        self.run_check(config)

        WMIMetric = self.load_class("WMIMetric")

        # Populate results and extract metrics
        results = load_fixture("win32_perfformatteddata_perfdisk_logicaldisk", ("Name", "_Total"))
        results += load_fixture("win32_perfformatteddata_perfdisk_logicaldisk", ("Name", "C:"))
        metrics = self.check._extract_metrics(results, "Name")

        # Assess
        expected_metrics = [
            WMIMetric("AvgDiskBytesPerWrite", 1536, ["name:_total"]),
            WMIMetric("FreeMegabytes", 19742, ["name:_total"]),
            WMIMetric("AvgDiskBytesPerWrite", 1536, ["name:c:"]),
            WMIMetric("FreeMegabytes", 19742, ["name:c:"]),
        ]

        self.assertEquals(metrics, expected_metrics)

    def test_mandatory_tag_by(self):
        """
        Exception is raised when the result returned by tge WMI query contains multiple rows
        but no `tag_by` value was given.
        """
        config = {
            'instances': [self.WMI_CONFIG_NO_TAG_BY]
        }
        with self.assertRaises(Exception):
            self.run_check(config)

    def test_filters(self):
        """
        Test the logic behind `_format_filter`
        """
        # Set up the check
        config = {
            'instances': [self.WMI_CONFIG_FILTER]
        }
        self.run_check(config)

        # Test `_format_filter` method
        no_filters = []
        filters = [{'Name': "SomeName"}, {'Id': "SomeId"}]

        self.assertEquals("", self.check._format_filter(no_filters))
        self.assertEquals(" WHERE Id = 'SomeId' AND Name = 'SomeName'",
                          self.check._format_filter(filters))

    def test_check(self):
        """
        Assess check coverage.
        """
        # Run the check
        config = {
            'instances': [self.WMI_CONFIG]
        }
        self.run_check(config)

        for _, mname, _ in self.WMI_CONFIG['metrics']:
            self.assertMetric(mname, count=2)

        self.coverage_report()
