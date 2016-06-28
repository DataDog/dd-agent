# stdlib
import re

# 3p
from mock import Mock

# project
from checks import AgentCheck
from tests.core.test_wmi import TestCommonWMI
from tests.checks.common import AgentCheckTest


class IISTestCase(AgentCheckTest, TestCommonWMI):
    CHECK_NAME = 'iis'

    WIN_SERVICES_MINIMAL_CONFIG = {
        'host': ".",
        'tags': ["mytag1", "mytag2"]
    }

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
        # Set up & run the check
        config = {
            'instances': [self.WIN_SERVICES_CONFIG]
        }
        logger = Mock()

        self.run_check_twice(config, mocks={'log': logger})

        # Test metrics
        # ... normalize site-names
        ok_site_name = re.sub(r"[,\+\*\-/()\[\]{}\s]", "_", config['instances'][0]['sites'][0])
        fail_site_name = re.sub(r"[,\+\*\-/()\[\]{}\s]", "_", config['instances'][0]['sites'][1])

        for mname in self.IIS_METRICS:
            self.assertMetric(mname, tags=["mytag1", "mytag2", "site:{0}".format(ok_site_name)], count=1)

        # Test service checks
        self.assertServiceCheck('iis.site_up', status=AgentCheck.OK,
                                tags=["site:{0}".format(ok_site_name)], count=1)
        self.assertServiceCheck('iis.site_up', status=AgentCheck.CRITICAL,
                                tags=["site:{0}".format(fail_site_name)], count=1)

        # Check completed with no warnings
        self.assertFalse(logger.warning.called)

        self.coverage_report()

    def test_check_2008(self):
        """
        Returns the right metrics and service checks for 2008 IIS
        """
        # Run check
        config = {
            'instances': [self.WIN_SERVICES_CONFIG]
        }
        config['instances'][0]['is_2008'] = True

        self.run_check_twice(config)

        # Test metrics

        # Normalize site-names
        ok_site_name = re.sub(r"[,\+\*\-/()\[\]{}\s]", "_", config['instances'][0]['sites'][0])
        fail_site_name = re.sub(r"[,\+\*\-/()\[\]{}\s]", "_", config['instances'][0]['sites'][1])
        for mname in self.IIS_METRICS:
            self.assertMetric(mname, tags=["mytag1", "mytag2", "site:{0}".format(ok_site_name)], count=1)

        # Test service checks
        self.assertServiceCheck('iis.site_up', status=AgentCheck.OK,
                                tags=["site:{0}".format(ok_site_name)], count=1)
        self.assertServiceCheck('iis.site_up', status=AgentCheck.CRITICAL,
                                tags=["site:{0}".format(fail_site_name)], count=1)

    def test_check_without_sites_specified(self):
        """
        Returns the right metrics and service checks for the `_Total` site
        """
        # Run check
        config = {
            'instances': [self.WIN_SERVICES_MINIMAL_CONFIG]
        }
        self.run_check_twice(config)

        for mname in self.IIS_METRICS:
            self.assertMetric(mname, tags=["mytag1", "mytag2"], count=1)

        self.assertServiceCheck('iis.site_up', status=AgentCheck.OK,
                                tags=["site:{0}".format('Total')], count=1)
        self.coverage_report()
