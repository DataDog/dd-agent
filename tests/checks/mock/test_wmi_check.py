# 3p
from mock import Mock

# project
from tests.checks.common import AgentCheckTest
from tests.core.test_wmi import SWbemServices, TestCommonWMI


class WMITestCase(AgentCheckTest, TestCommonWMI):
    CHECK_NAME = 'wmi_check'

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
        'tag_by': "Name",
        'constant_tags': ["foobar"],
    }

    WMI_NON_DIGIT_PROP = {
        'class': "Win32_PerfFormattedData_PerfDisk_LogicalDisk",
        'metrics': [["NonDigit", "winsys.nondigit", "gauge"],
                    ["FreeMegabytes", "winsys.disk.freemegabytes", "gauge"]],
    }

    WMI_MISSING_PROP_CONFIG = {
        'class': "Win32_PerfRawData_PerfOS_System",
        'metrics': [["UnknownCounter", "winsys.unknowncounter", "gauge"],
                    ["MissingProperty", "this.will.not.be.reported", "gauge"]],
    }

    WMI_CONFIG_NO_TAG_BY = {
        'class': "Win32_PerfFormattedData_PerfDisk_LogicalDisk",
        'metrics': [["AvgDiskBytesPerWrite", "winsys.disk.avgdiskbytesperwrite", "gauge"],
                    ["FreeMegabytes", "winsys.disk.freemegabytes", "gauge"]],
    }

    WMI_CONFIG_FILTERS = {
        'class': "Win32_PerfFormattedData_PerfDisk_LogicalDisk",
        'metrics': [["AvgDiskBytesPerWrite", "winsys.disk.avgdiskbytesperwrite", "gauge"],
                    ["FreeMegabytes", "winsys.disk.freemegabytes", "gauge"]],
        'filters': [{'Name': "_Total"}],
    }

    WMI_TAG_QUERY_CONFIG_TEMPLATE = {
        'class': "Win32_PerfFormattedData_PerfProc_Process",
        'metrics': [["IOReadBytesPerSec", "proc.io.bytes_read", "gauge"]],
        'filters': [{'Name': "chrome"}],
    }

    @classmethod
    def _make_wmi_tag_query_config(cls, tag_queries):
        """
        Helper to create a WMI configuration on
        `Win32_PerfFormattedData_PerfProc_Process.IOReadBytesPerSec` with the given
        `tag_queries` parameter.
        """
        wmi_tag_query_config = {}
        wmi_tag_query_config.update(cls.WMI_TAG_QUERY_CONFIG_TEMPLATE)

        queries = tag_queries if all(isinstance(elem, list) for elem in tag_queries) \
            else [tag_queries]

        wmi_tag_query_config['tag_queries'] = queries

        return wmi_tag_query_config

    def _get_wmi_sampler(self):
        """
        Helper to easily retrieve, if exists and unique, the WMISampler created
        by the configuration.

        Fails when multiple samplers are avaiable.
        """
        self.assertTrue(
            self.check.wmi_samplers,
            u"Unable to retrieve the WMISampler: no sampler was found"
        )
        self.assertEquals(
            len(self.check.wmi_samplers), 1,
            u"Unable to retrieve the WMISampler: expected a unique, but multiple were found"
        )

        return self.check.wmi_samplers.itervalues().next()

    def test_wmi_connection(self):
        """
        Establish a WMI connection to the specified host/namespace, with the right credentials.
        """
        # Run check
        config = {
            'instances': [self.WMI_CONNECTION_CONFIG]
        }
        self.run_check(config)

        # A WMISampler is cached
        self.assertInPartial("myhost:some/namespace:Win32_OperatingSystem", self.check.wmi_samplers)
        wmi_sampler = self.getProp(self.check.wmi_samplers, "myhost:some/namespace:Win32_OperatingSystem")

        # Connection was established with the right parameters
        self.assertWMIConn(wmi_sampler, "myhost")
        self.assertWMIConn(wmi_sampler, "some/namespace")

    def test_wmi_sampler_initialization(self):
        """
        An instance creates its corresponding WMISampler.
        """
        # Run check
        config = {
            'instances': [self.WMI_CONFIG_FILTERS]
        }
        self.run_check(config)

        # Retrieve the sampler
        wmi_sampler = self._get_wmi_sampler()

        # Assert the sampler
        self.assertEquals(wmi_sampler.class_name, "Win32_PerfFormattedData_PerfDisk_LogicalDisk")
        self.assertEquals(wmi_sampler.property_names, ["AvgDiskBytesPerWrite", "FreeMegabytes"])
        self.assertEquals(wmi_sampler.filters, [{'Name': "_Total"}])

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
        self.assertInPartial("myhost:some/namespace:Win32_OperatingSystem", self.check.wmi_props)
        metric_name_and_type_by_property, properties = \
            self.getProp(self.check.wmi_props, "myhost:some/namespace:Win32_OperatingSystem")

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
        # local import to avoid pulling in pywintypes ahead of time.
        from checks.wmi_check import WMIMetric  # noqa

        # Set up the check
        config = {
            'instances': [self.WMI_CONFIG]
        }
        self.run_check(config)

        # Retrieve the sampler
        wmi_sampler = self._get_wmi_sampler()

        # Extract metrics
        metrics = self.check._extract_metrics(wmi_sampler, "name", [], ["foobar"])

        # Assess
        expected_metrics = [
            WMIMetric("freemegabytes", 19742, ["foobar", "name:c:"]),
            WMIMetric("avgdiskbytesperwrite", 1536, ["foobar", "name:c:"]),
            WMIMetric("freemegabytes", 19742, ["foobar", "name:d:"]),
            WMIMetric("avgdiskbytesperwrite", 1536, ["foobar", "name:d:"]),
        ]
        self.assertEquals(metrics, expected_metrics)

    def test_missing_property(self):
        """
        Do not raise on missing properties, but print a warning.
        """
        # Set up the check
        config = {
            'instances': [self.WMI_MISSING_PROP_CONFIG]
        }
        logger = Mock()

        self.run_check(config, mocks={'log': logger})
        self.assertTrue(logger.warning.called)

    def test_warnings_on_non_digit(self):
        """
        Log a warning on non digit property values except for:
        * 'Name' property
        * 'tag_by' associated property
        """
        wmi_instance = self.WMI_NON_DIGIT_PROP.copy()
        config = {
            'instances': [wmi_instance]
        }
        logger = Mock()

        # Log a warning about 'NonDigit' property
        self.run_check(config, mocks={'log': logger})
        self.assertEquals(logger.warning.call_count, 1)

        # No warnings on `tag_by` property neither on `Name`
        del wmi_instance['metrics'][0]
        wmi_instance['tag_by'] = "NonDigit"
        self.run_check(config, mocks={'log': logger})
        self.assertEquals(logger.warning.call_count, 1)

    def test_query_timeouts(self):
        """
        Gracefully handle WMI query timeouts.
        """
        def __patched_init__(*args, **kwargs):
            """
            Force `timeout_duration` value.
            """
            kwargs['timeout_duration'] = 0.1
            return wmi_constructor(*args, **kwargs)

        # Increase WMI queries' runtime
        SWbemServices._exec_query_run_time = 0.2

        # Patch WMISampler to decrease timeout tolerance
        from checks.libs.wmi.sampler import WMISampler

        wmi_constructor = WMISampler.__init__
        WMISampler.__init__ = __patched_init__

        # Set up the check
        config = {
            'instances': [self.WMI_CONFIG]
        }
        logger = Mock()

        # No exception is raised but a WARNING is logged
        self.run_check(config, mocks={'log': logger})
        self.assertTrue(logger.warning.called)

    def test_mandatory_tag_by(self):
        """
        Exception is raised when the result returned by the WMI query contains multiple rows
        but no `tag_by` value was given.
        """
        # local import to avoid pulling in pywintypes ahead of time.
        from checks.wmi_check import MissingTagBy  # noqa

        # Valid configuration
        config = {
            'instances': [self.WMI_CONFIG]
        }
        self.run_check(config)

        # Invalid
        config = {
            'instances': [self.WMI_CONFIG_NO_TAG_BY]
        }

        self.assertRaises(MissingTagBy, self.run_check, config, force_reload=True)

    def test_query_tag_properties(self):
        """
        WMISampler's property list contains `metrics` and `tag_queries` ones.
        """
        # Set up the check
        tag_queries = ["IDProcess", "Win32_Process", "Handle", "CommandLine"]
        config = {
            'instances': [self._make_wmi_tag_query_config(tag_queries)]
        }
        self.run_check(config)

        # WMI props are cached
        self.assertInPartial(
            "localhost:root\\cimv2:Win32_PerfFormattedData_PerfProc_Process",
            self.check.wmi_props
        )
        _, properties = \
            self.getProp(self.check.wmi_props, "localhost:root\\cimv2:Win32_PerfFormattedData_PerfProc_Process")

        self.assertEquals(properties, ["IOReadBytesPerSec", "IDProcess"])

    def test_query_tags(self):
        """
        Tag extracted metrics with `tag_queries` queries.
        """
        # local import to avoid pulling in pywintypes ahead of time.
        from checks.wmi_check import WMIMetric # noqa

        # Set up the check
        tag_queries = ["IDProcess", "Win32_Process", "Handle", "CommandLine"]
        config = {
            'instances': [self._make_wmi_tag_query_config(tag_queries)]
        }
        self.run_check(config)

        # Retrieve the sampler
        wmi_sampler = self._get_wmi_sampler()

        # Extract metrics
        metrics = self.check._extract_metrics(
            wmi_sampler, "name",
            tag_queries=[tag_queries], constant_tags=["foobar"]
        )

        # Assess
        expected_metrics = [
            WMIMetric("ioreadbytespersec", 20455, tags=['foobar', 'commandline:c:\\'
                      'programfiles(x86)\\google\\chrome\\application\\chrome.exe']),
            WMIMetric('idprocess', 4036, tags=['foobar', 'commandline:c:\\'
                      'programfiles(x86)\\google\\chrome\\application\\chrome.exe']),
        ]
        self.assertEquals(metrics, expected_metrics)

    def test_query_tags_failures(self):
        """
        Check different `tag_queries` failure scenarios.
        """
        # Mock the logger so it can be traced
        logger = Mock()

        # Raise when user `tag_queries` input has a wrong format
        tag_queries = ["IDProcess", "MakesNoSense"]
        config = {
            'instances': [self._make_wmi_tag_query_config(tag_queries)]
        }

        self.assertRaises(IndexError, self.run_check, config, mocks={'log': logger})
        self.assertEquals(logger.error.call_count, 1)

        # Raise when user `link_source_property` is not a class's property
        tag_queries = ["UnknownProperty", "Win32_Process", "Handle", "CommandLine"]
        config = {
            'instances': [self._make_wmi_tag_query_config(tag_queries)]
        }
        self.assertRaises(
            TypeError, self.run_check, config,
            force_reload=True, mocks={'log': logger}
        )
        self.assertEquals(logger.error.call_count, 2)

        # Raise when user `target property` is not a target class's property
        tag_queries = ["IDProcess", "Win32_Process", "Handle", "UnknownProperty"]
        config = {
            'instances': [self._make_wmi_tag_query_config(tag_queries)]
        }
        self.assertRaises(
            TypeError, self.run_check, config,
            force_reload=True, mocks={'log': logger}
        )
        self.assertEquals(logger.error.call_count, 3)

        # Do not raise on result returned, print a warning and continue
        tag_queries = [
            "ResultNotMatchingAnyTargetProperty", "Win32_Process", "Handle", "CommandLine"
        ]
        config = {
            'instances': [self._make_wmi_tag_query_config(tag_queries)]
        }

        self.run_check(config, force_reload=True, mocks={'log': logger})
        self.assertTrue(logger.warning.called)

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
            self.assertMetric(mname, tags=["foobar", "name:c:"], count=1)
            self.assertMetric(mname, tags=["foobar", "name:d:"], count=1)

        self.coverage_report()
