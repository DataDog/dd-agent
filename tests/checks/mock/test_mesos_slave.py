from tests.checks.common import AgentCheckTest, get_check_class, Fixtures

from nose.plugins.attrib import attr
from mock import patch
from checks import AgentCheck
import json


def _mocked_get_state(*args, **kwargs):
    state = json.loads(Fixtures.read_file('state.json'))
    return state
def _mocked_get_stats(*args, **kwargs):
    stats = json.loads(Fixtures.read_file('stats.json'))
    return stats

@attr(requires='mesos_slave')
class TestMesosSlave(AgentCheckTest):
    CHECK_NAME = 'mesos_slave'

    def test_checks(self):
        config = {
            'init_config': {},
            'instances': [
                {
                    'url': 'http://localhost:5050',
                    'tasks': ['hello']
                }
            ]
        }

        klass = get_check_class('mesos_slave')
        with patch.object(klass, '_get_state', _mocked_get_state):
            with patch.object(klass, '_get_stats', _mocked_get_stats):
                check = klass('mesos_slave', {}, {})
                self.run_check_twice(config)
                metrics = {}
                for d in (check.SLAVE_TASKS_METRICS, check.SYSTEM_METRICS, check.SLAVE_RESOURCE_METRICS,
                          check.SLAVE_EXECUTORS_METRICS, check.STATS_METRICS):
                    metrics.update(d)
                [self.assertMetric(v[0]) for k, v in check.TASK_METRICS.iteritems()]
                [self.assertMetric(v[0]) for k, v in metrics.iteritems()]
                self.assertServiceCheck('hello.ok', count=1, status=AgentCheck.OK)
