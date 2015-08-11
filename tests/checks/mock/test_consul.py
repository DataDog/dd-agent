import random

from tests.checks.common import AgentCheckTest, load_check

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

MOCK_BAD_CONFIG = {
    'init_config': {},
    'instances' : [{ # Multiple instances should cause it to fail
        'url': 'http://localhost:8500',
        'catalog_checks': True,
        'new_leader_checks': True
    }, {
        'url': 'http://localhost:8501',
        'catalog_checks': True,
        'new_leader_checks': True
    }]
}

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

    def mock_get_local_config(self, instance):
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
        def _get_random_ip():
            rand_int = int(15 * random.random()) + 10
            return "10.0.2.{0}".format(rand_int)

        return [
            {
                "Address": _get_random_ip(),
                "Node": "node-1",
                "ServiceAddress": "",
                "ServiceID": service,
                "ServiceName": service,
                "ServicePort": 80,
                "ServiceTags": [
                    "az-us-east-1a"
                ]
            }
        ]

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
            '_get_cluster_leader': self.mock_get_cluster_leader_A
        }

    def test_bad_config(self):
        self.assertRaises(Exception, self.run_check, MOCK_BAD_CONFIG)

    # def test_get_nodes_in_cluster(self):
    #     self.run_check(MOCK_CONFIG, mocks=self._get_consul_mocks())
    #     self.assertMetric('consul.catalog.nodes_up', value=3, tags=['consul_datacenter:dc1'])

    # def test_get_services_in_cluster(self):
    #     self.run_check(MOCK_CONFIG, mocks=self._get_consul_mocks())
    #     self.assertMetric('consul.catalog.services_up', value=6, tags=['consul_datacenter:dc1'])


    def test_get_nodes_with_service(self):
        self.run_check(MOCK_CONFIG, mocks=self._get_consul_mocks())
        self.assertMetric('consul.catalog.nodes_up', value=1, tags=['consul_datacenter:dc1', 'consul_service_id:service-1'])

    def test_get_peers_in_cluster(self):
        mocks = self._get_consul_mocks()

        # When node is leader
        self.run_check(MOCK_CONFIG, mocks=mocks)
        self.assertMetric('consul.peers', value=3, tags=['consul_datacenter:dc1', 'mode:leader'])

        mocks['_get_cluster_leader'] = self.mock_get_cluster_leader_B

        # When node is follower
        self.run_check(MOCK_CONFIG, mocks=mocks)
        self.assertMetric('consul.peers', value=3, tags=['consul_datacenter:dc1', 'mode:follower'])


    def test_get_services_on_node(self):
        self.run_check(MOCK_CONFIG, mocks=self._get_consul_mocks())
        self.assertMetric('consul.catalog.services_up', value=6, tags=['consul_datacenter:dc1', 'consul_node_id:node-1'])

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
        self.check._last_known_leader = 'My Old Leader'

        mocks = self._get_consul_mocks()
        mocks['_get_cluster_leader'] = self.mock_get_cluster_leader_B

        self.run_check(MOCK_CONFIG_LEADER_CHECK, mocks=mocks)
        self.assertEqual(len(self.events), 1)

        event = self.events[0]
        self.assertEqual(event['event_type'], 'consul.new_leader')
        self.assertIn('prev_consul_leader:My Old Leader', event['tags'])
        self.assertIn('curr_consul_leader:My New Leader', event['tags'])
