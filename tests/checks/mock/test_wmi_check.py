# project
from tests.checks.common import AgentCheckTest


Win32_OperatingSystem_attr = {
    'BootDevice': "\\Device\\HarddiskVolume1",
    'BuildNumber': "9600",
    'BuildType': "Multiprocessor Free",
    'Caption': "Microsoft Windows Server 2012 R2 Standard Evaluation",
    'CodeSet': "1252",
    'CountryCode': "1",
    'CreationClassName': "Win32_OperatingSystem",
    'CSCreationClassName': "Win32_ComputerSystem",
    'CSName': "WIN-7022K3K6GF8",
    'CurrentTimeZone': -420,
    'DataExecutionPrevention_32BitApplications': True,
    'DataExecutionPrevention_Available': True,
    'DataExecutionPrevention_Drivers': True,
    'DataExecutionPrevention_SupportPolicy': 3,
    'Debug': False,
    'Description': "",
    'Distributed': False,
    'EncryptionLevel': 256,
    'ForegroundApplicationBoost': 2,
    'FreePhysicalMemory': "3238796",
    'FreeSpaceInPagingFiles': "720896",
    'FreeVirtualMemory': "3936028",
    'InstallDate': "20140729152415.000000-420",
    'LastBootUpTime': "20150331151024.957920-420",
    'LocalDateTime': "20150331152210.670000-420",
    'Locale': "0409",
    'Manufacturer': "Microsoft Corporation",
    'MaxNumberOfProcesses': 4294967295,
    'MaxProcessMemorySize': "137438953344",
    'MUILanguages': "en-US",
    'Name': "Microsoft Windows Server 2012 R2 Standard Evaluation"
            "|C:\\Windows|\\Device\\Harddisk0\\Partition2",
    'NumberOfProcesses': 60,
    'NumberOfUsers': 2,
    'OperatingSystemSKU': 79,
    'Organization': "",
    'OSArchitecture': "64-bit",
    'OSLanguage': 1033,
    'OSProductSuite': 272,
    'OSType': 18,
    'PortableOperatingSystem': False,
    'Primary': True,
    'ProductType': 3,
    'RegisteredUser': "Windows User",
    'SerialNumber': "00252-10000-00000-AA228",
    'ServicePackMajorVersion': 0,
    'ServicePackMinorVersion': 0,
    'SizeStoredInPagingFiles': "720896",
    'Status': "OK",
    'SuiteMask': 272,
    'SystemDevice': "\\Device\\HarddiskVolume2",
    'SystemDirectory': "C:\\Windows\\system32",
    'SystemDrive': "C:",
    'TotalVirtualMemorySize': "4914744",
    'TotalVisibleMemorySize': "4193848",
    'Version': "6.3.9600",
    'WindowsDirectory': "C:\\Windows",
}

Win32_PerfFormattedData_PerfProc_Process_attr = {
    'CreatingProcessID': 2976,
    'ElapsedTime': "2673",
    'HandleCount': 461,
    'IDProcess': 4036,
    'IODataBytesPersec': "219808",
    'IODataOperationsPersec': "1049",
    'IOOtherBytesPersec': "0",
    'IOOtherOperationsPersec': "1699",
    'IOReadBytesPerSec': "20455",
    'IOReadOperationsPersec': "505",
    'IOWriteBytesPersec': "199353",
    'IOWriteOperationsPersec': "544",
    'Name': "chrome",
    'PageFaultsPersec': 3,
    'PageFileBytes': "98619392",
    'PageFileBytesPeak': "98619392",
    'PercentPrivilegedTime': "12",
    'PercentProcessorTime': "18",
    'PercentUserTime': "6",
    'PoolNonpagedBytes': 28128,
    'PoolPagedBytes': 325216,
    'PriorityBase': 8,
    'PrivateBytes': "98619392",
    'ThreadCount': 9,
    'VirtualBytes': "303472640",
    'VirtualBytesPeak': "304521216",
    'WorkingSet': "112803840",
    'WorkingSetPeak': "112803840",
    'WorkingSetPrivate': "82731008",
}

Win32_Process_attr = {
    'CommandLine': "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe\"",
    'Handle': "3264"
}


class Mocked_Win32_Service(object):
    """
    Generate Mocked Win32 Service from given attributes
    """
    def __init__(self, **entries):
        self.__dict__.update(entries)

    def query(self, q):
        if q == "SELECT CommandLine FROM Win32_Process WHERE Handle = 4036":
            return [Mocked_Win32_Service(**Win32_Process_attr)]
        else:
            return []


class Mocked_WMI(object):
    """
    Mock WMI methods for test purpose
    """
    def __init__(self, mocked_wmi_classes):
        # Make WMI classes callable
        def get_wmi_obj(wmi_obj):
            return lambda Name=None: [wmi_obj] if not Name or wmi_obj.Name == Name else []

        for wmi_class, wmi_obj in mocked_wmi_classes.iteritems():
            mocked_wmi_classes[wmi_class] = get_wmi_obj(wmi_obj)

        self._mocked_classes = mocked_wmi_classes

    def WMI(self, host, user, password):
        """
        Return a mock WMI object with a mock class
        """
        return Mocked_Win32_Service(**self._mocked_classes)


class WMITestCase(AgentCheckTest):
    CHECK_NAME = 'wmi_check'

    CONFIG = {
        'class': "Win32_OperatingSystem",
        'metrics': [["NumberOfProcesses", "system.proc.count", "gauge"],
                    ["NumberOfUsers", "system.users.count", "gauge"]],
        'constant_tags': ["mytag"]
    }

    FILTER_CONFIG = {
        'class': "Win32_PerfFormattedData_PerfProc_Process",
        'metrics': [["ThreadCount", "my_app.threads.count", "gauge"],
                    ["VirtualBytes", "my_app.mem.virtual", "gauge"]],
        'filters': [{'Name': "chrome"}],
        'tag_by': "Name"
    }

    TAG_QUERY_CONFIG = {
        'class': "Win32_PerfFormattedData_PerfProc_Process",
        'metrics': [["IOReadBytesPerSec", "proc.io.bytes_read", "gauge"]],
        'filters': [{'Name': "chrome"}],
        'tag_queries': [["IDProcess", "Win32_Process", "Handle", "CommandLine"]]
    }

    def setUp(self):
        # Mocking `wmi` Python package
        import sys
        sys.modules['wmi'] = Mocked_WMI(
            {
                'Win32_OperatingSystem': Mocked_Win32_Service(**Win32_OperatingSystem_attr),
                'Win32_PerfFormattedData_PerfProc_Process':
                    Mocked_Win32_Service(**Win32_PerfFormattedData_PerfProc_Process_attr),
            })

    def test_check(self):
        """
        Collect WMI metrics + `constant_tags`
        """
        # Run check
        config = {
            'instances': [self.CONFIG]
        }

        self.run_check(config)

        # Test metrics
        for _, mname, _ in self.CONFIG['metrics']:
            self.assertMetric(mname, tags=self.CONFIG['constant_tags'], count=1)

        self.coverage_report()

    def test_filter_and_tagging(self):
        """
        Test `filters` and `tag_by` parameters
        """
        # Run check
        config = {
            'instances': [self.FILTER_CONFIG]
        }
        self.run_check(config)

        # Test metrics
        for _, mname, _ in self.FILTER_CONFIG['metrics']:
            self.assertMetric(mname, tags=["name:chrome"], count=1)

        self.coverage_report()

    def test_tag_queries(self):
        """
        Test `tag_queries` parameter
        """
        # Run check
        config = {
            'instances': [self.TAG_QUERY_CONFIG]
        }
        self.run_check(config)

        # Test metrics
        for _, mname, _ in self.TAG_QUERY_CONFIG['metrics']:
            self.assertMetric(mname, tags=['commandline:c:\\program_files_(x86)\\google'
                                           '\\chrome\\application\\chrome.exe"'], count=1)

        self.coverage_report()
