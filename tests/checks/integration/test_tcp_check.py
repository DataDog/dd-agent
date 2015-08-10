# stdlibb
import time

# 3p
from nose.plugins.attrib import attr

# project
from tests.checks.common import AgentCheckTest

RESULTS_TIMEOUT = 5

CONFIG = {
    'init_config': {},
    'instances': [{
        'host': '127.0.0.1',
        'port': 65530,
        'timeout': 1,
        'name': 'DownService'
    }, {
        'host': '126.0.0.1',
        'port': 65530,
        'timeout': 1,
        'name': 'DownService2'
    }, {
        'host': 'datadoghq.com',
        'port': 80,
        'timeout': 1,
        'name': 'UpService'
    }]
}


@attr(requires='network')
class TCPCheckTest(AgentCheckTest):
    CHECK_NAME = 'tcp_check'

    def tearDown(self):
        self.check.stop()

    def wait_for_async(self, method, attribute, count):
        """
        Loop on `self.check.method` until `self.check.attribute >= count`.

        Raise after
        """
        i = 0
        while i < RESULTS_TIMEOUT:
            self.check._process_results()
            if len(getattr(self.check, attribute)) >= count:
                return getattr(self.check, method)()
            time.sleep(1)
            i += 1
        raise Exception("Didn't get the right count of service checks in time {0}"
                        .format(getattr(self.check, attribute)))

    def test_event_deprecation(self):
        """
        Deprecate events usage for service checks.
        """
        # Run the check
        self.run_check(CONFIG)

        # Overrides self.service_checks attribute when values are available
        self.warnings = self.wait_for_async('get_warnings', 'warnings', 3)

        # Assess warnings
        self.assertWarning(
            "Using events for service checks is deprecated in "
            "favor of monitors and will be removed in future versions of the "
            "Datadog Agent.",
            count=3
        )

    def test_check(self):
        """
        Check coverage.
        """
        # Run the check
        self.run_check(CONFIG)

        # Overrides self.service_checks attribute when values are available
        self.service_checks = self.wait_for_async('get_service_checks', 'service_checks', 3)

        expected_tags = ["instance:DownService", "target_host:127.0.0.1", "port:65530"]
        self.assertServiceCheckCritical("tcp.can_connect", tags=expected_tags)

        expected_tags = ["instance:DownService2", "target_host:126.0.0.1", "port:65530"]
        self.assertServiceCheckCritical("tcp.can_connect", tags=expected_tags)

        expected_tags = ["instance:UpService", "target_host:datadoghq.com", "port:80"]
        self.assertServiceCheckOK("tcp.can_connect", tags=expected_tags)

        self.coverage_report()
