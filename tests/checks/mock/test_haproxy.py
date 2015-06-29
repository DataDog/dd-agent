# stdlib
from collections import defaultdict

# 3p
from nose.plugins.attrib import attr

# project
from tests.checks.common import AgentCheckTest, Fixtures


@attr(requires='haproxy')
class HaproxyTest(AgentCheckTest):

    CHECK_NAME = 'haproxy'

    def test_count_per_statuses(self):
        data = Fixtures.read_file('haproxy_status').splitlines()

        # per service
        self.check._process_data(data, True, False, collect_status_metrics=True,
                                 collect_status_metrics_by_host=False)

        expected_hosts_statuses = defaultdict(int)
        expected_hosts_statuses[('b', 'OPEN')] = 1
        expected_hosts_statuses[('b', 'UP')] = 3
        expected_hosts_statuses[('a', 'OPEN')] = 1
        self.assertEquals(self.check.hosts_statuses, expected_hosts_statuses)

        # with collect_aggregates_only set to True
        self.check._process_data(data, True, True, collect_status_metrics=True,
                                 collect_status_metrics_by_host=False)
        self.assertEquals(self.check.hosts_statuses, expected_hosts_statuses)

        # per host
        self.check._process_data(data, True, False, collect_status_metrics=True,
                                 collect_status_metrics_by_host=True)
        expected_hosts_statuses = defaultdict(int)
        expected_hosts_statuses[('b', 'FRONTEND', 'OPEN')] = 1
        expected_hosts_statuses[('a', 'FRONTEND', 'OPEN')] = 1
        expected_hosts_statuses[('b', 'i-1', 'UP')] = 1
        expected_hosts_statuses[('b', 'i-2', 'UP')] = 1
        expected_hosts_statuses[('b', 'i-3', 'UP')] = 1
        self.assertEquals(self.check.hosts_statuses, expected_hosts_statuses)

        self.check._process_data(data, True, True, collect_status_metrics=True,
                                 collect_status_metrics_by_host=True)
        self.assertEquals(self.check.hosts_statuses, expected_hosts_statuses)
