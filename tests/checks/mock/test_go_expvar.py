# stdlib
from collections import defaultdict
import copy
import time

# 3p
import simplejson as json

# project
from tests.checks.common import AgentCheckTest, Fixtures


def _get_data_mock(url):
    with open(url, 'r') as go_output:
        return json.loads(go_output.read())


class TestGoExpVar(AgentCheckTest):

    CHECK_NAME = 'go_expvar'

    CHECK_GAUGES = [
        'go_expvar.memstats.alloc',
        'go_expvar.memstats.heap_alloc',
        'go_expvar.memstats.heap_idle',
        'go_expvar.memstats.heap_inuse',
        'go_expvar.memstats.heap_objects',
        'go_expvar.memstats.heap_released',
        'go_expvar.memstats.heap_sys',
        'go_expvar.memstats.total_alloc',
    ]

    CHECK_GAUGES_DEFAULT = [
        'go_expvar.memstats.pause_ns.95percentile',
        'go_expvar.memstats.pause_ns.avg',
        'go_expvar.memstats.pause_ns.count',
        'go_expvar.memstats.pause_ns.max',
        'go_expvar.memstats.pause_ns.median',
    ]

    CHECK_GAUGES_CUSTOM_MOCK = {
        'go_expvar.gauge1': ['metric_tag1:metric_value1',
                             'metric_tag2:metric_value2',
                             'path:random_walk'],
        'go_expvar.memstats.by_size.1.mallocs': []
    }

    CHECK_RATES = [
        'go_expvar.memstats.frees',
        'go_expvar.memstats.lookups',
        'go_expvar.memstats.mallocs',
        'go_expvar.memstats.num_gc',
        'go_expvar.memstats.pause_total_ns',
    ]

    CHECK_RATES_CUSTOM_MOCK = ['go_expvar.gc.pause']

    def __init__(self, *args, **kwargs):
        AgentCheckTest.__init__(self, *args, **kwargs)
        self._expvar_url = Fixtures.file('expvar_output')
        self.mock_config = {
            "instances": [{
                "expvar_url": self._expvar_url,
                "tags": ["optionaltag1", "optionaltag2"],
                "metrics": [
                    {
                        # Contains list traversal and default values
                        "path": "memstats/BySize/1/Mallocs",
                    },
                    {
                        "path": "memstats/PauseTotalNs",
                        "alias": "go_expvar.gc.pause",
                        "type": "rate"
                    },
                    {
                        "path": "random_walk",
                        "alias": "go_expvar.gauge1",
                        "type": "gauge",
                        "tags": ["metric_tag1:metric_value1", "metric_tag2:metric_value2"]
                    }
                ]
            }]
        }
        self.mocks = {
            '_get_data': _get_data_mock,
        }
        self.config = {
            "instances": [{
                "expvar_url": 'http://localhost:8079/debug/vars',
                'tags': ['my_tag'],
                'metrics': [
                    {
                        'path': 'last_user'
                    },
                    {
                        'path': 'num_calls',
                        "type": "rate"
                    },
                ]
            }]
        }

    def _run_check_twice(self):
        # To avoid the disparition of some gauges during the second check
        mocks = self.mocks.copy()
        config = self.mock_config
        expvar_url = self._expvar_url

        fake_last_gc_count = defaultdict(int)
        mocks['_last_gc_count'] = fake_last_gc_count

        # Can't use run_check_twice due to specific metrics
        self.run_check(config, mocks=mocks)
        time.sleep(1)
        # Reset it
        del fake_last_gc_count[expvar_url]

        self.run_check(config, mocks=mocks)

    def test_go_expvar_mocked(self):
        self._run_check_twice()

        shared_tags = ['optionaltag1', 'optionaltag2', 'expvar_url:{0}'.format(self._expvar_url)]

        for gauge in self.CHECK_GAUGES + self.CHECK_GAUGES_DEFAULT:
            self.assertMetric(gauge, count=1, tags=shared_tags)
        for gauge, tags in self.CHECK_GAUGES_CUSTOM_MOCK.iteritems():
            self.assertMetric(gauge, count=1, tags=shared_tags + tags)

        for rate in self.CHECK_RATES:
            self.assertMetric(rate, count=1, tags=shared_tags)
        for rate in self.CHECK_RATES_CUSTOM_MOCK:
            self.assertMetric(rate, count=1, tags=shared_tags + ['path:memstats.PauseTotalNs'])

        self.coverage_report()

    def test_max_metrics(self):
        config_max = copy.deepcopy(self.mock_config)
        config_max['instances'][0]['max_returned_metrics'] = 1

        self.run_check(config_max, mocks=self.mocks)
        shared_tags = ['optionaltag1', 'optionaltag2', 'expvar_url:{0}'.format(self._expvar_url)]

        # Default metrics
        for gauge in self.CHECK_GAUGES_DEFAULT:
            self.assertMetric(gauge, count=1, tags=shared_tags)
        # And then check limitation, will fail at the coverage_report if incorrect
        self.assertMetric('go_expvar.memstats.alloc', count=1, tags=shared_tags)

        self.coverage_report()

    def test_deep_get(self):
        # Wildcard for dictkeys
        content = {
            'a': {
                'one': 1,
                'two': 2
            },
            'b': {
                'three': 3,
                'four':  4
            }
        }
        expected = [
            (['a', 'two'], 2),
            (['b', 'three'], 3),
        ]
        self.run_check(self.mock_config, mocks=self.mocks)
        results = self.check.deep_get(content, ['.', 't.*'], [])
        self.assertEqual(sorted(results), sorted(expected))

        expected = [(['a', 'one'], 1)]
        results = self.check.deep_get(content, ['.', 'one'], [])
        self.assertEqual(results, expected)

        # Wildcard for list index
        content = {
            'list': [
                {
                    'timestamp': 10,
                    'value':     5
                },
                {
                    'timestamp': 10,
                    'value':     10
                },
                {
                    'timestamp': 10,
                    'value':     20
                }
            ]
        }
        expected = [
            (['list', '0', 'value'], 5),
            (['list', '1', 'value'], 10),
            (['list', '2', 'value'], 20)
        ]

        results = self.check.deep_get(content, ['list', '.*', 'value'], [])
        self.assertEqual(sorted(results), sorted(expected))
