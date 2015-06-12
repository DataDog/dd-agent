# stdlib
import socket

# 3p
from nose.plugins.attrib import attr

# project
from tests.checks.common import AgentCheckTest


@attr(requires='riak')
class RiakTestCase(AgentCheckTest):

    CHECK_NAME = 'riak'

    CHECK_GAUGES = [
        'riak.memory_atom',
        'riak.memory_atom_used',
        'riak.memory_binary',
        'riak.memory_code',
        'riak.memory_ets',
        'riak.memory_processes',
        'riak.memory_processes_used',
        'riak.memory_total',
        'riak.node_get_fsm_active_60s',
        'riak.node_get_fsm_in_rate',
        'riak.node_gets',
        'riak.node_put_fsm_active_60s',
        'riak.node_put_fsm_in_rate',
        'riak.node_put_fsm_out_rate',
        'riak.node_put_fsm_rejected_60s',
        'riak.node_puts',
        'riak.pbc_active',
        'riak.pbc_connects',
        'riak.read_repairs',
        'riak.vnode_gets',
        'riak.vnode_index_deletes',
        'riak.vnode_index_reads',
        'riak.vnode_index_writes',
        'riak.vnode_puts',
    ]

    CHECK_GAUGES_STATS = [
        'riak.node_get_fsm_objsize_100',
        'riak.node_get_fsm_objsize_95',
        'riak.node_get_fsm_objsize_99',
        'riak.node_get_fsm_objsize_mean',
        'riak.node_get_fsm_objsize_median',
        'riak.node_get_fsm_siblings_100',
        'riak.node_get_fsm_siblings_95',
        'riak.node_get_fsm_siblings_99',
        'riak.node_get_fsm_siblings_mean',
        'riak.node_get_fsm_siblings_median',
        'riak.node_get_fsm_time_100',
        'riak.node_get_fsm_time_95',
        'riak.node_get_fsm_time_99',
        'riak.node_get_fsm_time_mean',
        'riak.node_get_fsm_time_median',
        'riak.node_put_fsm_time_100',
        'riak.node_put_fsm_time_95',
        'riak.node_put_fsm_time_99',
        'riak.node_put_fsm_time_mean',
        'riak.node_put_fsm_time_median',
    ]

    # FIXME
    # Does not appear when null and we can't really fake it
    # These metrics do not appear in the docs
    # http://docs.basho.com/riak/latest/ops/running/stats-and-monitoring/
    CHECK_NOT_TESTED = [
        'riak.node_get_fsm_out_rate',
        'riak.node_get_fsm_rejected_60s',
    ]

    SERVICE_CHECK_NAME = 'riak.can_connect'

    def test_riak(self):
        config_dev1 = {
            "instances": [{
                "url": "http://localhost:10018/stats",
                "tags": ["my_tag"]
            }]
        }
        self.run_check(config_dev1)
        tags = ['my_tag']
        sc_tags = tags + ['url:' + config_dev1['instances'][0]['url']]

        for gauge in self.CHECK_GAUGES + self.CHECK_GAUGES_STATS:
            self.assertMetric(gauge, count=1, tags=tags)

        self.assertServiceCheckOK(self.SERVICE_CHECK_NAME,
                                  tags=sc_tags,
                                  count=1)
        self.coverage_report()

    def test_bad_config(self):
        self.assertRaises(
            socket.error,
            lambda: self.run_check({"instances": [{"url": "http://localhost:5985"}]})
        )
        sc_tags = ['url:http://localhost:5985']

        self.assertServiceCheckCritical(self.SERVICE_CHECK_NAME,
                                        tags=sc_tags,
                                        count=1)
        self.coverage_report()
