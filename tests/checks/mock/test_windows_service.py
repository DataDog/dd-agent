# stdlib
from mock import Mock

# project
from checks import AgentCheck
from tests.checks.common import AgentCheckTest


WinHttpAutoProxySvc_attr = {                        # Running Windows Service
    'AcceptPause': False,
    'AcceptStop': True,
    'Caption': "WinHTTP Web Proxy Auto-Discovery Service",
    'CheckPoint': 0,
    'CreationClassName': "Win32_Service",
    'Description': "WinHTTP implements the client HTTP stack and provides developers"
                   " with a Win32 API and COM Automation component for sending HTTP requests"
                   " and receiving responses. In addition, WinHTTP provides support "
                   " for auto-discovering a proxy configuration via its implementation"
                   " of the Web Proxy Auto-Discovery (WPAD) protocol.",
    'DesktopInteract': False,
    'DisplayName': "WinHTTP Web Proxy Auto-Discovery Service",
    'ErrorControl': "Normal",
    'ExitCode': 0,
    'Name': "WinHttpAutoProxySvc",
    'PathName': "C:\\Windows\\system32\\svchost.exe -k LocalService",
    'ProcessId': 864,
    'ServiceSpecificExitCode': 0,
    'ServiceType': "Share Process",
    'Started': True,
    'StartMode': "Manual",
    'StartName': "NT AUTHORITY\\LocalService",
    'State': "Running",
    'Status': "OK",
    'SystemCreationClassName': "Win32_ComputerSystem",
    'SystemName': "WIN-7022K3K6GF8",
    'TagId': 0,
    'WaitHint': 0,
}


WSService_attr = {                                  # Stopped Windows Service
    'AcceptPause': False,
    'AcceptStop': False,
    'Caption': "Windows Store Service (WSService)",
    'CheckPoint': 0,
    'CreationClassName': "Win32_Service",
    'Description': "Provides infrastructure support for Windows Store."
                   "This service is started on demand and if ded applications"
                   " bought using Windows Store will not behave correctly.",
    'DesktopInteract': False,
    'DisplayName': "Windows Store Service (WSService)",
    'ErrorControl': "Normal",
    'ExitCode': 1077,
    'Name': "WSService",
    'PathName': "C:\\Windows\\System32\\svchost.exe -k wsappx",
    'ProcessId': 0,
    'ServiceSpecificExitCode': 0,
    'ServiceType': "Share Process",
    'Started': False,
    'StartMode': "Manual",
    'StartName': "LocalSystem",
    'State': "Stopped",
    'Status': "OK",
    'SystemCreationClassName': "Win32_ComputerSystem",
    'SystemName': "WIN-7022K3K6GF8",
    'TagId': 0,
    'WaitHint': 0,
}


class Mocked_Win32_Service(object):
    """
    Generate Mocked Win32 Service from given attributes
    """
    def __init__(self, **entries):
        self.__dict__.update(entries)


class Mocked_WMI(Mock):
    """
    Mock WMI methods for test purpose
    """
    def Win32_Service(self, name):
        """
        Returns mock match Win32 Service
        """
        if name == "WinHttpAutoProxySvc":
            return [Mocked_Win32_Service(**WinHttpAutoProxySvc_attr)]
        if name == "WSService":
            return [Mocked_Win32_Service(**WSService_attr)]
        return []


class WindowsServiceTestCase(AgentCheckTest):
    CHECK_NAME = 'windows_service'

    WIN_SERVICES_CONFIG = {
        'host': ".",
        'services': ["WinHttpAutoProxySvc", "WSService"]
    }

    def test_check(self):
        """
        Returns the right service checks
        """
        # Mocking `wmi` Python package
        import sys
        sys.modules['wmi'] = Mocked_WMI()

        # Run check
        config = {
            'instances': [self.WIN_SERVICES_CONFIG]
        }

        self.run_check(config)

        # Test service checks
        self.assertServiceCheck('windows_service.state', status=AgentCheck.OK, count=1,
                                tags=[u'service:WinHttpAutoProxySvc',
                                      u'host:' + self.check.hostname])
        self.assertServiceCheck('windows_service.state', status=AgentCheck.CRITICAL, count=1,
                                tags=[u'service:WSService',
                                      u'host:' + self.check.hostname])

        self.coverage_report()
