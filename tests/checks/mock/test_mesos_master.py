# stdlib
import json

# 3p
from mock import patch
from nose.plugins.attrib import attr

# project
from tests.checks.common import AgentCheckTest, Fixtures, get_check_class


def _mocked_get_master_state(*args, **kwargs):
    state = json.loads(Fixtures.read_file('state.json'))
    return state


def _mocked_get_master_stats(*args, **kwargs):
    stats = json.loads(Fixtures.read_file('stats.json'))
    return stats


def _mocked_get_master_roles(*args, **kwargs):
    roles = json.loads(Fixtures.read_file('roles.json'))
    return roles


@attr(requires='mesos_master')
class TestMesosMaster(AgentCheckTest):
    CHECK_NAME = 'mesos_master'

    def test_checks(self):
        config = {
            'init_config': {},
            'instances': [
                {
                    'url': 'http://localhost:5050'
                }
            ]
        }

        klass = get_check_class('mesos_master')
        with patch.object(klass, '_get_master_state', _mocked_get_master_state):
            with patch.object(klass, '_get_master_stats', _mocked_get_master_stats):
                with patch.object(klass, '_get_master_roles', _mocked_get_master_roles):
                    check = klass('mesos_master', {}, {})
                    self.run_check_twice(config)
                    metrics = {}
                    for d in (check.CLUSTER_TASKS_METRICS, check.CLUSTER_SLAVES_METRICS,
                              check.CLUSTER_RESOURCES_METRICS, check.CLUSTER_REGISTRAR_METRICS,
                              check.CLUSTER_FRAMEWORK_METRICS, check.SYSTEM_METRICS, check.STATS_METRICS):
                        metrics.update(d)
                    [self.assertMetric(v[0]) for k, v in check.FRAMEWORK_METRICS.iteritems()]
                    [self.assertMetric(v[0]) for k, v in metrics.iteritems()]
                    [self.assertMetric(v[0]) for k, v in check.ROLE_RESOURCES_METRICS.iteritems()]
                    self.assertMetric('mesos.cluster.total_frameworks')
                    self.assertMetric('mesos.framework.total_tasks')
                    self.assertMetric('mesos.role.frameworks.count')
                    self.assertMetric('mesos.role.weight')
