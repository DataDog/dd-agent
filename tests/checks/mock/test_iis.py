import re

# project
from checks import AgentCheck
from tests.core.test_wmi import TestCommonWMI
from tests.checks.common import AgentCheckTest


class IISTestCase(AgentCheckTest, TestCommonWMI):
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
        # Run check
        config = {
            'instances': [self.WIN_SERVICES_CONFIG]
        }

        self.run_check_twice(config)

        # Test metrics

        # normalize site-names
        ok_site_name = re.sub(r"[,\+\*\-/()\[\]{}\s]", "_", config['instances'][0]['sites'][0])
        fail_site_name = re.sub(r"[,\+\*\-/()\[\]{}\s]", "_", config['instances'][0]['sites'][1])
        for mname in self.IIS_METRICS:
            self.assertMetric(mname, tags=["mytag1", "mytag2", "site:{0}".format(ok_site_name)], count=1)

        # Test service checks
        self.assertServiceCheck('iis.site_up', status=AgentCheck.OK,
                                tags=["site:{0}".format(ok_site_name)], count=1)
        self.assertServiceCheck('iis.site_up', status=AgentCheck.CRITICAL,
                                tags=["site:{0}".format(fail_site_name)], count=1)

        self.coverage_report()
