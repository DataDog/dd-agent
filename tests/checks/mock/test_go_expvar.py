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
        'memstats.alloc',
        'memstats.heap_alloc',
        'memstats.heap_idle',
        'memstats.heap_inuse',
        'memstats.heap_objects',
        'memstats.heap_released',
        'memstats.heap_sys',
        'memstats.total_alloc',
    ]

    CHECK_GAUGES_DEFAULT = [
        'memstats.pause_ns.95percentile',
        'memstats.pause_ns.avg',
        'memstats.pause_ns.count',
        'memstats.pause_ns.max',
        'memstats.pause_ns.median',
    ]

    CHECK_GAUGES_CUSTOM_MOCK = {
        'gauge1': ['metric_tag1:metric_value1',
                   'metric_tag2:metric_value2',
                   'path:random_walk'],
        'memstats.by_size.1.mallocs': []
    }

    CHECK_RATES = [
        'memstats.frees',
        'memstats.lookups',
        'memstats.mallocs',
        'memstats.num_gc',
        'memstats.pause_total_ns',
    ]

    CHECK_RATES_CUSTOM_MOCK = ['gc.pause']

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
            self.assertMetric("{0}.{1}".format(self.CHECK_NAME, gauge), count=1, tags=shared_tags)
        for gauge, tags in self.CHECK_GAUGES_CUSTOM_MOCK.iteritems():
            self.assertMetric("{0}.{1}".format(self.CHECK_NAME, gauge), count=1, tags=shared_tags + tags)

        for rate in self.CHECK_RATES:
            self.assertMetric("{0}.{1}".format(self.CHECK_NAME, rate), count=1, tags=shared_tags)
        for rate in self.CHECK_RATES_CUSTOM_MOCK:
            self.assertMetric("{0}.{1}".format(self.CHECK_NAME, rate), count=1, tags=shared_tags + ['path:memstats.PauseTotalNs'])

        self.coverage_report()

    def test_go_expvar_mocked_namespace(self):
        metric_namespace = "testingapp"

        # adjust mock config to set a namespace value
        self.mock_config = {
            "instances": [{
                "namespace": metric_namespace,
                "expvar_url": self._expvar_url,
                "tags": ["optionaltag1", "optionaltag2"],
                "metrics": [
                    {
                        # Contains list traversal and default values
                        "path": "memstats/BySize/1/Mallocs",
                    },
                    {
                        "path": "memstats/PauseTotalNs",
                        "alias": "{0}.gc.pause".format(metric_namespace),
                        "type": "rate"
                    },
                    {
                        "path": "random_walk",
                        "alias": "{0}.gauge1".format(metric_namespace),
                        "type": "gauge",
                        "tags": ["metric_tag1:metric_value1", "metric_tag2:metric_value2"]
                    }
                ]
            }]
        }

        self._run_check_twice()

        shared_tags = ['optionaltag1', 'optionaltag2', 'expvar_url:{0}'.format(self._expvar_url)]

        for gauge in self.CHECK_GAUGES + self.CHECK_GAUGES_DEFAULT:
            self.assertMetric("{0}.{1}".format(metric_namespace, gauge), count=1, tags=shared_tags)
        for gauge, tags in self.CHECK_GAUGES_CUSTOM_MOCK.iteritems():
            self.assertMetric("{0}.{1}".format(metric_namespace, gauge), count=1, tags=shared_tags + tags)

        for rate in self.CHECK_RATES:
            self.assertMetric("{0}.{1}".format(metric_namespace, rate), count=1, tags=shared_tags)
        for rate in self.CHECK_RATES_CUSTOM_MOCK:
            self.assertMetric("{0}.{1}".format(metric_namespace, rate), count=1, tags=shared_tags + ['path:memstats.PauseTotalNs'])

        self.coverage_report()

    def test_max_metrics(self):
        config_max = copy.deepcopy(self.mock_config)
        config_max['instances'][0]['max_returned_metrics'] = 1

        self.run_check(config_max, mocks=self.mocks)
        shared_tags = ['optionaltag1', 'optionaltag2', 'expvar_url:{0}'.format(self._expvar_url)]

        # Default metrics
        for gauge in self.CHECK_GAUGES_DEFAULT:
            self.assertMetric("{0}.{1}".format(self.CHECK_NAME, gauge), count=1, tags=shared_tags)
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
