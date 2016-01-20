# Aerospike agent check for Datadog Agent.
# Copyright (C) 2015 Pippio, Inc. All rights reserved.

# stdlib
import socket
from contextlib import closing

# project
from checks import AgentCheck


EVENT_TYPE = 'aerospike'
SERVICE_CHECK_NAME = '%s.server_up' % EVENT_TYPE


class Aerospike(AgentCheck):
    """Collect metrics and events from Aerospike server(s)."""

    def __init__(self, name, init_config, agentConfig, instances=None):
        AgentCheck.__init__(self, name, init_config,
                            agentConfig, instances=instances)
        self.connection_pool = {}

    def check(self, instance):
        """Run the Aerospike check for one instance."""

        # Required parameters
        host = instance['host']
        port = int(instance['port'])

        # Optional parameters
        want_metrics = set(instance.get('metrics', []))
        want_namespace_metrics = set(instance.get('namespace_metrics', []))
        namespaces = instance.get('namespaces', None)

        key = '%s:%d' % (host, port)
        conn = self.connection_pool.get(key, None)

        if conn is None:
            conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            conn.connect((host, port))
            self.connection_pool[key] = conn

        try:
            with closing(conn.makefile('r')) as fp:
                if namespaces is None:
                    # Probe all namespaces by default.
                    conn.send('namespaces\r\n')
                    namespaces = fp.readline().rstrip().split(';')

                conn.send('statistics\r\n')
                self._send_metrics(fp, want_metrics)

                for n in namespaces:
                    conn.send('namespace/%s\r\n' % n)
                    tags = {'namespace': n}
                    self._send_metrics(fp, want_namespace_metrics, tags)

            self.service_check(SERVICE_CHECK_NAME, AgentCheck.OK)
        except socket.error:
            self.log.exception('Error connecting to Aerospike at %s', key)
            del self.connection_pool[key]

    def _send_metrics(self, fp, only_keys=[], tags={}):
        vals = dict(x.split('=', 1) for x in fp.readline().rstrip().split(';'))
        if only_keys:
            # Cherry pick only desired metrics, if they exist.
            for skey in only_keys:
                value = vals.get(skey, None)
                if value and value.isdigit():
                    self.gauge(self._make_key(skey), value, tags=tags)
        else:
            # Present all metrics.
            for skey, value in vals.items():
                if value.isdigit():
                    self.gauge(self._make_key(skey), value, tags=tags)

    @staticmethod
    def _make_key(n):
        return '%s.%s' % (EVENT_TYPE, n.replace('-', '_'))
