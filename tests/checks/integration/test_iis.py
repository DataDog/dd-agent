# 3p
from nose.plugins.attrib import attr

# project
from tests.checks.common import AgentCheckTest

MINIMAL_INSTANCE = {
    'host': '.',
}

INSTANCE = {
    'host': '.',
    'sites': ['Default Web Site', 'Test-Website-1', 'Non Existing Website'],
}

INVALID_HOST_INSTANCE = {
    'host': 'nonexistinghost'
}


@attr('windows')
@attr(requires='windows')
class IISTest(AgentCheckTest):
    CHECK_NAME = 'iis'

    IIS_METRICS = (
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
    )

    def test_basic_check(self):
        self.run_check_twice({'instances': [MINIMAL_INSTANCE]})

        for metric in self.IIS_METRICS:
            self.assertMetric(metric, tags=[], count=1)

        self.assertServiceCheckOK('iis.site_up', tags=["site:{0}".format('Total')], count=1)
        self.coverage_report()

    def test_check_on_specific_websites(self):
        self.run_check_twice({'instances': [INSTANCE]})

        site_tags = ['Default_Web_Site', 'Test_Website_1']
        for metric in self.IIS_METRICS:
            for site_tag in site_tags:
                self.assertMetric(metric, tags=["site:{0}".format(site_tag)], count=1)

        self.assertServiceCheckOK('iis.site_up',
                                  tags=["site:{0}".format('Default_Web_Site')], count=1)
        self.assertServiceCheckOK('iis.site_up',
                                  tags=["site:{0}".format('Test_Website_1')], count=1)
        self.assertServiceCheckCritical('iis.site_up',
                                        tags=["site:{0}".format('Non_Existing_Website')], count=1)

        self.coverage_report()

    def test_service_check_with_invalid_host(self):
        self.run_check({'instances': [INVALID_HOST_INSTANCE]})

        self.assertServiceCheckCritical('iis.site_up', tags=["site:{0}".format('Total')])

        self.coverage_report()
