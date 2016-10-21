import random

from tests.checks.common import AgentCheckTest, load_check
from utils.containers import hash_mutable

MOCK_CONFIG = {
    'init_config': {},
    'instances' : [{
        'url': 'http://localhost:8500',
        'catalog_checks': True,
    }]
}

MOCK_CONFIG_SERVICE_WHITELIST = {
    'init_config': {},
    'instances' : [{
        'url': 'http://localhost:8500',
        'catalog_checks': True,
        'service_whitelist': ['service_{0}'.format(k) for k in range(70)]
    }]
}

MOCK_CONFIG_LEADER_CHECK = {
    'init_config': {},
    'instances' : [{
        'url': 'http://localhost:8500',
        'catalog_checks': True,
        'new_leader_checks': True
    }]
}

MOCK_CONFIG_SELF_LEADER_CHECK = {
    'init_config': {},
    'instances' : [{
        'url': 'http://localhost:8500',
        'catalog_checks': True,
        'self_leader_check': True
    }]
}

MOCK_CONFIG_NETWORK_LATENCY_CHECKS = {
    'init_config': {},
    'instances' : [{
        'url': 'http://localhost:8500',
        'catalog_checks': True,
        'network_latency_checks': True
    }]
}

MOCK_BAD_CONFIG = {
    'init_config': {},
    'instances' : [{ # Multiple instances should cause it to fail
        'url': 'http://localhost:8500',
        'catalog_checks': True,
        'new_leader_checks': True
    }, {
        'url': 'http://localhost:8501',
        'catalog_checks': True,
        'new_leader_checks': True,
        'self_leader_check': True
    }]
}

def _get_random_ip():
    rand_int = int(15 * random.random()) + 10
    return "10.0.2.{0}".format(rand_int)

class TestCheckConsul(AgentCheckTest):
    CHECK_NAME = 'consul'

    def mock_get_peers_in_cluster(self, instance):
        return [
            "10.0.2.14:8300",
            "10.0.2.15:8300",
            "10.0.2.16:8300"
        ]

    def mock_get_services_in_cluster(self, instance):
        return {
            "service-1": [
                "az-us-east-1a"
            ],
            "service-2": [
                "az-us-east-1a"
            ],
            "service-3": [
                "az-us-east-1a"
            ],
            "service-4": [
                "az-us-east-1a"
            ],
            "service-5": [
                "az-us-east-1a"
            ],
            "service-6": [
                "az-us-east-1a"
            ]
        }

    def mock_get_n_services_in_cluster(self, n):
        dct = {}
        for i in range(n):
            k = "service_{0}".format(i)
            dct[k] = []
        return dct

    def mock_get_local_config(self, instance, instance_state):
        return {
            "Config": {
                "AdvertiseAddr": "10.0.2.15",
                "Datacenter": "dc1",
                "Ports": {
                    "DNS": 8600,
                    "HTTP": 8500,
                    "HTTPS": -1,
                    "RPC": 8400,
                    "SerfLan": 8301,
                    "SerfWan": 8302,
                    "Server": 8300
                },
            }
        }

    def mock_get_nodes_in_cluster(self, instance):
        return [
            {
                "Address": "10.0.2.15",
                "Node": "node-1"
            },
            {
                "Address": "10.0.2.25",
                "Node": "node-2"
            },
            {
                "Address": "10.0.2.35",
                "Node": "node-2"
            },
        ]


    def mock_get_nodes_with_service(self, instance, service):

        return [
            {
                "Checks": [
                    {
                        "CheckID": "serfHealth",
                        "Name": "Serf Health Status",
                        "Node": "node-1",
                        "Notes": "",
                        "Output": "Agent alive and reachable",
                        "ServiceID": "",
                        "ServiceName": "",
                        "Status": "passing"
                    },
                    {
                        "CheckID": "service:{0}".format(service),
                        "Name": "service check {0}".format(service),
                        "Node": "node-1",
                        "Notes": "",
                        "Output": "Service {0} alive".format(service),
                        "ServiceID": service,
                        "ServiceName": "",
                        "Status": "passing"
                    }
                ],
                "Node": {
                    "Address": _get_random_ip(),
                    "Node": "node-1"
                },
                "Service": {
                    "Address": "",
                    "ID": service,
                    "Port": 80,
                    "Service": service,
                    "Tags": [
                        "az-us-east-1a"
                    ]
                }
            }
        ]

    def mock_get_nodes_with_service_warning(self, instance, service):

        return [
            {
                "Checks": [
                    {
                        "CheckID": "serfHealth",
                        "Name": "Serf Health Status",
                        "Node": "node-1",
                        "Notes": "",
                        "Output": "Agent alive and reachable",
                        "ServiceID": "",
                        "ServiceName": "",
                        "Status": "passing"
                    },
                    {
                        "CheckID": "service:{0}".format(service),
                        "Name": "service check {0}".format(service),
                        "Node": "node-1",
                        "Notes": "",
                        "Output": "Service {0} alive".format(service),
                        "ServiceID": service,
                        "ServiceName": "",
                        "Status": "warning"
                    }
                ],
                "Node": {
                    "Address": _get_random_ip(),
                    "Node": "node-1"
                },
                "Service": {
                    "Address": "",
                    "ID": service,
                    "Port": 80,
                    "Service": service,
                    "Tags": [
                        "az-us-east-1a"
                    ]
                }
            }
        ]


    def mock_get_nodes_with_service_critical(self, instance, service):

        return [
            {
                "Checks": [
                    {
                        "CheckID": "serfHealth",
                        "Name": "Serf Health Status",
                        "Node": "node-1",
                        "Notes": "",
                        "Output": "Agent alive and reachable",
                        "ServiceID": "",
                        "ServiceName": "",
                        "Status": "passing"
                    },
                    {
                        "CheckID": "service:{0}".format(service),
                        "Name": "service check {0}".format(service),
                        "Node": "node-1",
                        "Notes": "",
                        "Output": "Service {0} alive".format(service),
                        "ServiceID": service,
                        "ServiceName": "",
                        "Status": "warning"
                    },
                    {
                        "CheckID": "service:{0}".format(service),
                        "Name": "service check {0}".format(service),
                        "Node": "node-1",
                        "Notes": "",
                        "Output": "Service {0} alive".format(service),
                        "ServiceID": service,
                        "ServiceName": "",
                        "Status": "critical"
                    }
                ],
                "Node": {
                    "Address": _get_random_ip(),
                    "Node": "node-1"
                },
                "Service": {
                    "Address": "",
                    "ID": service,
                    "Port": 80,
                    "Service": service,
                    "Tags": [
                        "az-us-east-1a"
                    ]
                }
            }
        ]

    def mock_get_coord_datacenters(self, instance):
        return [{
            "Datacenter": "dc1",
            "Coordinates": [
                {
                    "Node": "host-1",
                    "Coord": {
                        "Vec": [
                            0.036520147625677804,
                            -0.00453289164613373,
                            -0.020523210880196232,
                            -0.02699760529719879,
                            -0.02689207977655939,
                            -0.01993826834797845,
                            -0.013022029942846501,
                            -0.002101656069659926
                        ],
                        "Error": 0.11137306578107628,
                        "Adjustment": -0.00021065907491393056,
                        "Height": 1.1109163532378512e-05
                    }
                }]
        }, {
            "Datacenter": "dc2",
            "Coordinates": [
                {
                    "Node": "host-2",
                    "Coord": {
                        "Vec": [
                            0.03548568620505946,
                            -0.0038202417296129025,
                            -0.01987440114252717,
                            -0.026223108843980016,
                            -0.026581965209197853,
                            -0.01891384862245717,
                            -0.013677323575279184,
                            -0.0014257906933581217
                        ],
                        "Error": 0.06388569381495224,
                        "Adjustment": -0.00036731776343708724,
                        "Height": 8.962823816793629e-05
                    }
                }]

        }]

    def mock_get_coord_nodes(self, instance):
        return [{
            "Node": "host-1",
            "Coord": {
                "Vec": [
                    0.007682993877165208,
                    0.002411059340215172,
                    0.0016420746641640123,
                    0.0037411046929292906,
                    0.004541946058965728,
                    0.0032195622863890523,
                    -0.0039447666794166095,
                    -0.0021767019427297815
                ],
                "Error": 0.28019529748212335,
                "Adjustment": -9.966407036439966e-05,
                "Height": 0.00011777098790169723
            }
        }, {
            "Node": "host-2",
            "Coord": {
                "Vec": [
                    0.007725239390196322,
                    0.0025160987581685982,
                    0.0017412811939227935,
                    0.003740935739394932,
                    0.004628794642643524,
                    0.003190871896051593,
                    -0.004058197296573195,
                    -0.002108437352702053
                ],
                "Error": 0.31518043241386984,
                "Adjustment": -0.00012274366490350246,
                "Height": 0.00015006836008626717
            }
        }]

    def mock_get_cluster_leader_A(self, instance):
        return '10.0.2.15:8300'

    def mock_get_cluster_leader_B(self, instance):
        return 'My New Leader'

    def _get_consul_mocks(self):
        return {
            'get_services_in_cluster': self.mock_get_services_in_cluster,
            'get_nodes_with_service': self.mock_get_nodes_with_service,
            'get_peers_in_cluster': self.mock_get_peers_in_cluster,
            '_get_local_config': self.mock_get_local_config,
            '_get_cluster_leader': self.mock_get_cluster_leader_A,
            '_get_coord_datacenters': self.mock_get_coord_datacenters,
            '_get_coord_nodes': self.mock_get_coord_nodes,
        }

    def test_get_nodes_with_service(self):
        self.run_check(MOCK_CONFIG, mocks=self._get_consul_mocks())
        self.assertMetric('consul.catalog.nodes_up', value=1, tags=['consul_datacenter:dc1', 'consul_service_id:service-1'])
        self.assertMetric('consul.catalog.nodes_passing', value=1, tags=['consul_datacenter:dc1', 'consul_service_id:service-1'])
        self.assertMetric('consul.catalog.nodes_warning', value=0, tags=['consul_datacenter:dc1', 'consul_service_id:service-1'])
        self.assertMetric('consul.catalog.nodes_critical', value=0, tags=['consul_datacenter:dc1', 'consul_service_id:service-1'])
        self.assertMetric('consul.catalog.services_up', value=6, tags=['consul_datacenter:dc1', 'consul_node_id:node-1'])
        self.assertMetric('consul.catalog.services_passing', value=6, tags=['consul_datacenter:dc1', 'consul_node_id:node-1'])
        self.assertMetric('consul.catalog.services_warning', value=0, tags=['consul_datacenter:dc1', 'consul_node_id:node-1'])
        self.assertMetric('consul.catalog.services_critical', value=0, tags=['consul_datacenter:dc1', 'consul_node_id:node-1'])

    def test_get_nodes_with_service_warning(self):
        my_mocks = self._get_consul_mocks()
        my_mocks['get_nodes_with_service'] = self.mock_get_nodes_with_service_warning

        self.run_check(MOCK_CONFIG, mocks=my_mocks)
        self.assertMetric('consul.catalog.nodes_up', value=1, tags=['consul_datacenter:dc1', 'consul_service_id:service-1'])
        self.assertMetric('consul.catalog.nodes_passing', value=0, tags=['consul_datacenter:dc1', 'consul_service_id:service-1'])
        self.assertMetric('consul.catalog.nodes_warning', value=1, tags=['consul_datacenter:dc1', 'consul_service_id:service-1'])
        self.assertMetric('consul.catalog.nodes_critical', value=0, tags=['consul_datacenter:dc1', 'consul_service_id:service-1'])
        self.assertMetric('consul.catalog.services_up', value=6, tags=['consul_datacenter:dc1', 'consul_node_id:node-1'])
        self.assertMetric('consul.catalog.services_passing', value=0, tags=['consul_datacenter:dc1', 'consul_node_id:node-1'])
        self.assertMetric('consul.catalog.services_warning', value=6, tags=['consul_datacenter:dc1', 'consul_node_id:node-1'])
        self.assertMetric('consul.catalog.services_critical', value=0, tags=['consul_datacenter:dc1', 'consul_node_id:node-1'])

    def test_get_nodes_with_service_critical(self):
        my_mocks = self._get_consul_mocks()
        my_mocks['get_nodes_with_service'] = self.mock_get_nodes_with_service_critical

        self.run_check(MOCK_CONFIG, mocks=my_mocks)
        self.assertMetric('consul.catalog.nodes_up', value=1, tags=['consul_datacenter:dc1', 'consul_service_id:service-1'])
        self.assertMetric('consul.catalog.nodes_passing', value=0, tags=['consul_datacenter:dc1', 'consul_service_id:service-1'])
        self.assertMetric('consul.catalog.nodes_warning', value=0, tags=['consul_datacenter:dc1', 'consul_service_id:service-1'])
        self.assertMetric('consul.catalog.nodes_critical', value=1, tags=['consul_datacenter:dc1', 'consul_service_id:service-1'])
        self.assertMetric('consul.catalog.services_up', value=6, tags=['consul_datacenter:dc1', 'consul_node_id:node-1'])
        self.assertMetric('consul.catalog.services_passing', value=0, tags=['consul_datacenter:dc1', 'consul_node_id:node-1'])
        self.assertMetric('consul.catalog.services_warning', value=0, tags=['consul_datacenter:dc1', 'consul_node_id:node-1'])
        self.assertMetric('consul.catalog.services_critical', value=6, tags=['consul_datacenter:dc1', 'consul_node_id:node-1'])

    def test_get_peers_in_cluster(self):
        mocks = self._get_consul_mocks()

        # When node is leader
        self.run_check(MOCK_CONFIG, mocks=mocks)
        self.assertMetric('consul.peers', value=3, tags=['consul_datacenter:dc1', 'mode:leader'])

        mocks['_get_cluster_leader'] = self.mock_get_cluster_leader_B

        # When node is follower
        self.run_check(MOCK_CONFIG, mocks=mocks)
        self.assertMetric('consul.peers', value=3, tags=['consul_datacenter:dc1', 'mode:follower'])

    def test_cull_services_list(self):
        self.check = load_check(self.CHECK_NAME, MOCK_CONFIG_LEADER_CHECK, self.DEFAULT_AGENT_CONFIG)

        # Pad num_services to kick in truncation logic
        num_services = self.check.MAX_SERVICES + 20

        # Big whitelist
        services = self.mock_get_n_services_in_cluster(num_services)
        whitelist = ['service_{0}'.format(k) for k in range(num_services)]
        self.assertEqual(len(self.check._cull_services_list(services, whitelist)), self.check.MAX_SERVICES)

        # Whitelist < MAX_SERVICES should spit out the whitelist
        services = self.mock_get_n_services_in_cluster(num_services)
        whitelist = ['service_{0}'.format(k) for k in range(self.check.MAX_SERVICES-1)]
        self.assertEqual(set(self.check._cull_services_list(services, whitelist)), set(whitelist))

        # No whitelist, still triggers truncation
        whitelist = []
        self.assertEqual(len(self.check._cull_services_list(services, whitelist)), self.check.MAX_SERVICES)

        # Num. services < MAX_SERVICES should be no-op in absence of whitelist
        num_services = self.check.MAX_SERVICES - 1
        services = self.mock_get_n_services_in_cluster(num_services)
        self.assertEqual(len(self.check._cull_services_list(services, whitelist)), num_services)

        # Num. services < MAX_SERVICES should spit out only the whitelist when one is defined
        num_services = self.check.MAX_SERVICES - 1
        whitelist = ['service_1', 'service_2', 'service_3']
        services = self.mock_get_n_services_in_cluster(num_services)
        self.assertEqual(set(self.check._cull_services_list(services, whitelist)), set(whitelist))

    def test_new_leader_event(self):
        self.check = load_check(self.CHECK_NAME, MOCK_CONFIG_LEADER_CHECK, self.DEFAULT_AGENT_CONFIG)
        instance_hash = hash_mutable(MOCK_CONFIG_LEADER_CHECK['instances'][0])
        self.check._instance_states[instance_hash].last_known_leader = 'My Old Leader'

        mocks = self._get_consul_mocks()
        mocks['_get_cluster_leader'] = self.mock_get_cluster_leader_B

        self.run_check(MOCK_CONFIG_LEADER_CHECK, mocks=mocks)
        self.assertEqual(len(self.events), 1)

        event = self.events[0]
        self.assertEqual(event['event_type'], 'consul.new_leader')
        self.assertIn('prev_consul_leader:My Old Leader', event['tags'])
        self.assertIn('curr_consul_leader:My New Leader', event['tags'])

    def test_self_leader_event(self):
        self.check = load_check(self.CHECK_NAME, MOCK_CONFIG_SELF_LEADER_CHECK, self.DEFAULT_AGENT_CONFIG)
        instance_hash = hash_mutable(MOCK_CONFIG_SELF_LEADER_CHECK['instances'][0])
        self.check._instance_states[instance_hash].last_known_leader = 'My Old Leader'

        mocks = self._get_consul_mocks()

        our_url = self.mock_get_cluster_leader_A(None)
        other_url = self.mock_get_cluster_leader_B(None)

        # We become the leader
        mocks['_get_cluster_leader'] = self.mock_get_cluster_leader_A
        self.run_check(MOCK_CONFIG_SELF_LEADER_CHECK, mocks=mocks)
        self.assertEqual(len(self.events), 1)
        self.assertEqual(our_url, self.check._instance_states[instance_hash].last_known_leader)
        event = self.events[0]
        self.assertEqual(event['event_type'], 'consul.new_leader')
        self.assertIn('prev_consul_leader:My Old Leader', event['tags'])
        self.assertIn('curr_consul_leader:%s' % our_url, event['tags'])

        # We are already the leader, no new events
        self.run_check(MOCK_CONFIG_SELF_LEADER_CHECK, mocks=mocks)
        self.assertEqual(len(self.events), 0)

        # We lose the leader, no new events
        mocks['_get_cluster_leader'] = self.mock_get_cluster_leader_B
        self.run_check(MOCK_CONFIG_SELF_LEADER_CHECK, mocks=mocks)
        self.assertEqual(len(self.events), 0)
        self.assertEqual(other_url, self.check._instance_states[instance_hash].last_known_leader)

        # We regain the leadership
        mocks['_get_cluster_leader'] = self.mock_get_cluster_leader_A
        self.run_check(MOCK_CONFIG_SELF_LEADER_CHECK, mocks=mocks)
        self.assertEqual(len(self.events), 1)
        self.assertEqual(our_url, self.check._instance_states[instance_hash].last_known_leader)
        event = self.events[0]
        self.assertEqual(event['event_type'], 'consul.new_leader')
        self.assertIn('prev_consul_leader:%s' % other_url, event['tags'])
        self.assertIn('curr_consul_leader:%s' % our_url, event['tags'])

    def test_network_latency_checks(self):
        self.check = load_check(self.CHECK_NAME, MOCK_CONFIG_NETWORK_LATENCY_CHECKS,
                                self.DEFAULT_AGENT_CONFIG)

        mocks = self._get_consul_mocks()

        # We start out as the leader, and stay that way
        instance_hash = hash_mutable(MOCK_CONFIG_NETWORK_LATENCY_CHECKS['instances'][0])
        self.check._instance_states[instance_hash].last_known_leader = self.mock_get_cluster_leader_A(None)

        self.run_check(MOCK_CONFIG_NETWORK_LATENCY_CHECKS, mocks=mocks)

        latency = [m for m in self.metrics if m[0].startswith('consul.net.')]
        latency.sort()
        # Make sure we have the expected number of metrics
        self.assertEquals(19, len(latency))

        # Only 3 dc-latency metrics since we only do source = self
        dc = [m for m in latency if '.dc.latency.' in m[0]]
        self.assertEquals(3, len(dc))
        self.assertEquals(1.6746410750238774, dc[0][2])

        # 16 latency metrics, 2 nodes * 8 metrics each
        node = [m for m in latency if '.node.latency.' in m[0]]
        self.assertEquals(16, len(node))
        self.assertEquals(0.26577747932995816, node[0][2])
