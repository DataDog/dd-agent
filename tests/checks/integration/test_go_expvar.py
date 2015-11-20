# stdlib
from collections import defaultdict
import time

# 3p
from nose.plugins.attrib import attr

# project
from tests.checks.common import AgentCheckTest


@attr(requires='go_expvar')
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

    CHECK_GAUGES_CUSTOM = {'go_expvar.last_user': '123456'}

    CHECK_RATES = [
        'go_expvar.memstats.frees',
        'go_expvar.memstats.lookups',
        'go_expvar.memstats.mallocs',
        'go_expvar.memstats.num_gc',
        'go_expvar.memstats.pause_total_ns',
    ]

    CHECK_RATES_CUSTOM = {'go_expvar.num_calls': 0}

    def __init__(self, *args, **kwargs):
        AgentCheckTest.__init__(self, *args, **kwargs)
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
        mocks = {}
        config = self.config
        expvar_url = self.config['instances'][0]['expvar_url']

        fake_last_gc_count = defaultdict(int)
        mocks['_last_gc_count'] = fake_last_gc_count

        # Can't use run_check_twice due to specific metrics
        self.run_check(config, mocks=mocks)
        time.sleep(1)
        # Reset it
        del fake_last_gc_count[expvar_url]

        self.run_check(config, mocks=mocks)

    # Real integration test
    def test_go_expvar(self):
        self._run_check_twice()

        shared_tags = [
            'my_tag',
            'expvar_url:{0}'.format(self.config['instances'][0]['expvar_url'])
        ]

        for gauge in self.CHECK_GAUGES + self.CHECK_GAUGES_DEFAULT:
            self.assertMetric(gauge, count=1, tags=shared_tags)
        for rate in self.CHECK_RATES:
            self.assertMetric(rate, count=1, tags=shared_tags)

        for gauge, value in self.CHECK_GAUGES_CUSTOM.iteritems():
            self.assertMetric(gauge, count=1, value=value, tags=shared_tags)
        for rate, value in self.CHECK_RATES_CUSTOM.iteritems():
            self.assertMetric(rate, count=1, value=value, tags=shared_tags)

        self.coverage_report()
