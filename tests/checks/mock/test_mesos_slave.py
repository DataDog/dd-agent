# stdlib
import json

# project
from checks import AgentCheck
from tests.checks.common import AgentCheckTest, Fixtures, get_check_class


class TestMesosSlave(AgentCheckTest):
    CHECK_NAME = 'mesos_slave'

    def test_checks(self):
        config = {
            'init_config': {},
            'instances': [
                {
                    'url': 'http://localhost:5051',
                    'tasks': ['hello']
                }
            ]
        }

        mocks = {
            '_get_stats': lambda x, y, z: json.loads(Fixtures.read_file('stats.json')),
            '_get_state': lambda x, y, z: json.loads(Fixtures.read_file('state.json'))
        }

        klass = get_check_class('mesos_slave')
        check = klass('mesos_slave', {}, {})
        self.run_check_twice(config, mocks=mocks)
        metrics = {}
        for d in (check.SLAVE_TASKS_METRICS, check.SYSTEM_METRICS, check.SLAVE_RESOURCE_METRICS,
                  check.SLAVE_EXECUTORS_METRICS, check.STATS_METRICS):
            metrics.update(d)
        [self.assertMetric(v[0]) for k, v in check.TASK_METRICS.iteritems()]
        [self.assertMetric(v[0]) for k, v in metrics.iteritems()]
        self.assertServiceCheck('hello.ok', count=1, status=AgentCheck.OK)
