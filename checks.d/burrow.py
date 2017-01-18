# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
import urlparse

# 3rd party
import requests

# project
from checks import AgentCheck
from config import _is_affirmative


class Burrow(AgentCheck):

    LIST_CLUSTERS = '/v2/kafka'
    CLUSTER_DETAILS = '/v2/kafka/{cluster}'
    LIST_CONSUMERS = '/v2/kafka/{cluster}/consumer'
    CONSUMER_LAG = '/v2/kafka/{cluster}/consumer/{consumer}/lag'

    @staticmethod
    def _check_for_error(req):
        if req.status_code != 200:
            raise Exception("Got {} error from burrow http endpoint".format(req.status_code))

        res = req.json()
        if res['error']:
            raise Exception("Got error from burrow http endpoint: {}".format(res['message']))

        return res

    def __init__(self, name, init_config, agentConfig, instances=None):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances)

    def check(self, instance):
        if 'status_url' not in instance:
            raise Exception("Missing 'status_url' in Burrow config")

        url = instance['status_url']
        connect_timeout = int(instance.get('connect_timeout', 5))
        receive_timeout = int(instance.get('receive_timeout', 15))

        optional_tags = instance.get('tags', [])

        r = requests.get(url=url+Burrow.LIST_CLUSTERS)
        res = Burrow._check_for_error(r)
        clusters = res['clusters']

        for cluster in clusters:
            r = requests.get(url+Burrow.LIST_CONSUMERS.format(cluster=cluster))
            res = Burrow._check_for_error(r)
            consumers = res['consumers']

            for consumer in consumers:
                r = requests.get(url+Burrow.CONSUMER_LAG.format(
                    cluster=cluster,
                    consumer=consumer
                ))
                res = Burrow._check_for_error(r)
                status = res['status']

                for s in status['partitions']:
                    tags = optional_tags + [
                        "cluster:{}".format(cluster),
                        "consumer:{}".format(consumer),
                        "partition:{}".format(s['partition']),
                        "topic:{}".format(s['topic']),
                        "lag_checker:burrow"
                    ]
                    sc = AgentCheck.OK
                    if s['status'] == 'STOP':
                        sc = AgentCheck.UNKNOWN
                    elif s['status'] == 'WARNING':
                        sc = AgentCheck.WARNING
                    elif s['status'] == 'ERR':
                        sc = AgentCheck.CRITICAL
                    elif s['status'] == 'STALL':
                        # the offsets are being committed,
                        # but they are not changing and the lag is non-zero
                        sc = AgentCheck.WARNING

                    self.service_check('kafka.consumer.lag.status', sc, tags)
                    # We only consider the latest lag in the evaluation window
                    self.histogram('kafka.consumer.lag', s['end']['lag'], tags)
