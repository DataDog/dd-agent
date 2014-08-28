# stdlib
import time
from hashlib import md5
import socket

# project
from checks import AgentCheck

# 3rd party
import simplejson as json
from httplib2 import Http, HttpLib2Error

class Riak(AgentCheck):

    keys = [
        "vnode_gets",
        "vnode_puts",
        "vnode_index_reads",
        "vnode_index_writes",
        "vnode_index_deletes",
        "node_gets",
        "node_puts",
        "pbc_active",
        "pbc_connects",
        "memory_total",
        "memory_processes",
        "memory_processes_used",
        "memory_atom",
        "memory_atom_used",
        "memory_binary",
        "memory_code",
        "memory_ets",
        "read_repairs",
        "node_put_fsm_rejected_60s",
        "node_put_fsm_active_60s",
        "node_put_fsm_in_rate",
        "node_put_fsm_out_rate",
        "node_get_fsm_rejected_60s",
        "node_get_fsm_active_60s",
        "node_get_fsm_in_rate",
        "node_get_fsm_out_rate"
    ]

    stat_keys = [
        "node_get_fsm_siblings",
        "node_get_fsm_objsize",
        "node_get_fsm_time",
        "node_put_fsm_time"
      ]

    def __init__(self, name, init_config, agentConfig, instances=None):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances)
        for k in ["mean", "median", "95", "99", "100"]:
            [self.keys.append(m + "_" + k) for m in self.stat_keys]

        self.prev_coord_redirs_total = -1


    def check(self, instance):
        url             = instance['url']
        default_timeout = self.init_config.get('default_timeout', 5)
        timeout         = float(instance.get('timeout', default_timeout))

        aggregation_key = md5(url).hexdigest()

        try:
            h = Http(timeout=timeout)
            resp, content = h.request(url, "GET")

        except socket.timeout, e:
            self.timeout_event(url, timeout, aggregation_key)
            return

        except socket.error, e:
            self.timeout_event(url, timeout, aggregation_key)
            return

        except HttpLib2Error, e:
            self.timeout_event(url, timeout, aggregation_key)
            return

        if resp.status != 200:
            self.status_code_event(url, resp, aggregation_key)

        stats = json.loads(content)

        [self.gauge("riak." + k, stats[k]) for k in self.keys if k in stats]

        coord_redirs_total = stats["coord_redirs_total"]
        if self.prev_coord_redirs_total > -1:
            count = coord_redirs_total - self.prev_coord_redirs_total
            self.gauge('riak.coord_redirs', count)

        self.prev_coord_redirs_total = coord_redirs_total

    def timeout_event(self, url, timeout, aggregation_key):
        self.event({
            'timestamp': int(time.time()),
            'event_type': 'riak_check',
            'msg_title': 'riak check timeout',
            'msg_text': '%s timed out after %s seconds.' % (url, timeout),
            'aggregation_key': aggregation_key
        })

    def status_code_event(self, url, r, aggregation_key):
        self.event({
            'timestamp': int(time.time()),
            'event_type': 'riak_check',
            'msg_title': 'Invalid reponse code for riak check',
            'msg_text': '%s returned a status of %s' % (url, r.status_code),
            'aggregation_key': aggregation_key
        })