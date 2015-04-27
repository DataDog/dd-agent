from mock import Mock

# project
from checks import AgentCheck
from tests.checks.common import AgentCheckTest


Win32_PerfFormattedData_W3SVC_WebService_attr = {
    'AnonymousUsersPersec': 0,
    'BytesReceivedPersec': "0",
    'BytesSentPersec': "0",
    'BytesTotalPersec': "0",
    'CGIRequestsPersec': 0,
    'ConnectionAttemptsPersec': 0,
    'CopyRequestsPersec': 0,
    'CurrentAnonymousUsers': 0,
    'CurrentBlockedAsyncIORequests': 0,
    'Currentblockedbandwidthbytes': 0,
    'CurrentCALcountforauthenticatedusers': 0,
    'CurrentCALcountforSSLconnections': 0,
    'CurrentCGIRequests': 0,
    'CurrentConnections': 0,
    'CurrentISAPIExtensionRequests': 0,
    'CurrentNonAnonymousUsers': 0,
    'DeleteRequestsPersec': 0,
    'FilesPersec': 0,
    'FilesReceivedPersec': 0,
    'FilesSentPersec': 0,
    'GetRequestsPersec': 0,
    'HeadRequestsPersec': 0,
    'ISAPIExtensionRequestsPersec': 0,
    'LockedErrorsPersec': 0,
    'LockRequestsPersec': 0,
    'LogonAttemptsPersec': 0,
    'MaximumAnonymousUsers': 0,
    'MaximumCALcountforauthenticatedusers': 0,
    'MaximumCALcountforSSLconnections': 0,
    'MaximumCGIRequests': 0,
    'MaximumConnections': 0,
    'MaximumISAPIExtensionRequests': 0,
    'MaximumNonAnonymousUsers': 0,
    'MeasuredAsyncIOBandwidthUsage': 0,
    'MkcolRequestsPersec': 0,
    'MoveRequestsPersec': 0,
    'Name': "Default Web Site",
    'NonAnonymousUsersPersec': 0,
    'NotFoundErrorsPersec': 0,
    'OptionsRequestsPersec': 0,
    'OtherRequestMethodsPersec': 0,
    'PostRequestsPersec': 0,
    'PropfindRequestsPersec': 0,
    'ProppatchRequestsPersec': 0,
    'PutRequestsPersec': 0,
    'SearchRequestsPersec': 0,
    'ServiceUptime': 251,
    'TotalAllowedAsyncIORequests': 0,
    'TotalAnonymousUsers': 0,
    'TotalBlockedAsyncIORequests': 0,
    'Totalblockedbandwidthbytes': 0,
    'TotalBytesReceived': "0",
    'TotalBytesSent': "0",
    'TotalBytesTransferred': "0",
    'TotalCGIRequests': 0,
    'TotalConnectionAttemptsallinstances': 0,
    'TotalCopyRequests': 0,
    'TotalcountoffailedCALrequestsforauthenticatedusers': 0,
    'TotalcountoffailedCALrequestsforSSLconnections': 0,
    'TotalDeleteRequests': 0,
    'TotalFilesReceived': 0,
    'TotalFilesSent': 0,
    'TotalFilesTransferred': 0,
    'TotalGetRequests': 0,
    'TotalHeadRequests': 0,
    'TotalISAPIExtensionRequests': 0,
    'TotalLockedErrors': 0,
    'TotalLockRequests': 0,
    'TotalLogonAttempts': 0,
    'TotalMethodRequests': 0,
    'TotalMethodRequestsPersec': 0,
    'TotalMkcolRequests': 0,
    'TotalMoveRequests': 0,
    'TotalNonAnonymousUsers': 0,
    'TotalNotFoundErrors': 0,
    'TotalOptionsRequests': 0,
    'TotalOtherRequestMethods': 0,
    'TotalPostRequests': 0,
    'TotalPropfindRequests': 0,
    'TotalProppatchRequests': 0,
    'TotalPutRequests': 0,
    'TotalRejectedAsyncIORequests': 0,
    'TotalSearchRequests': 0,
    'TotalTraceRequests': 0,
    'TotalUnlockRequests': 0,
    'TraceRequestsPersec': 0,
    'UnlockRequestsPersec': 0,
}


class Mocked_Win32_PerfFormattedData_W3SVC_WebService(object):
    """
    Generate Mocked instance of Win32_PerfFormattedData_W3SVC_WebService
    """
    def __init__(self, **entries):
        self.__dict__.update(entries)


class Mocked_WMI(Mock):
    """
    Mock WMI methods for test purpose
    """
    def Win32_PerfFormattedData_W3SVC_WebService(self):
        """
        Returns mock match Win32_PerfFormattedData_W3SVC_WebService
        """
        return [Mocked_Win32_PerfFormattedData_W3SVC_WebService(
                **Win32_PerfFormattedData_W3SVC_WebService_attr)]


class IISTestCase(AgentCheckTest):
    CHECK_NAME = 'iis'

    WIN_SERVICES_CONFIG = {
        'host': ".",
        'tags': ["mytag1", "mytag2"],
        'sites': ["Default Web Site", "Failing site"]
    }

    IIS_METRICS = [
        'iis.uptime',
        # Network
        'iis.net.bytes_sent',
        'iis.net.bytes_rcvd',
        'iis.net.bytes_total',
        'iis.net.num_connections',
        'iis.net.files_sent',
        'iis.net.files_rcvd',
        'iis.net.connection_attempts',
        # HTTP Methods
        'iis.httpd_request_method.get',
        'iis.httpd_request_method.post',
        'iis.httpd_request_method.head',
        'iis.httpd_request_method.put',
        'iis.httpd_request_method.delete',
        'iis.httpd_request_method.options',
        'iis.httpd_request_method.trace',
        # Errors
        'iis.errors.not_found',
        'iis.errors.locked',
        # Users
        'iis.users.anon',
        'iis.users.nonanon',
        # Requests
        'iis.requests.cgi',
        'iis.requests.isapi',
    ]

    def test_check(self):
        """
        Returns the right metrics and service checks
        """
        # Mocking `wmi` Python package
        import sys
        sys.modules['wmi'] = Mocked_WMI()

        # Run check
        config = {
            'instances': [self.WIN_SERVICES_CONFIG]
        }

        self.run_check_twice(config)

        # Test metrics
        for mname in self.IIS_METRICS:
            self.assertMetric(mname, tags=["mytag1", "mytag2", "site:Default Web Site"], count=1)

        # Test service checks
        self.assertServiceCheck('iis.site_up', status=AgentCheck.OK,
                                tags=["site:Default Web Site"], count=1)
        self.assertServiceCheck('iis.site_up', status=AgentCheck.CRITICAL,
                                tags=["site:Failing site"], count=1)

        self.coverage_report()
