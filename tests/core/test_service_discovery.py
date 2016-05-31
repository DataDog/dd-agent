# stdlib
import copy
import mock
import unittest

# project
from utils.service_discovery.config_stores import get_config_store
from utils.service_discovery.consul_config_store import ConsulStore
from utils.service_discovery.etcd_config_store import EtcdStore
from utils.service_discovery.abstract_config_store import AbstractConfigStore
from utils.service_discovery.sd_backend import get_sd_backend
from utils.service_discovery.sd_docker_backend import SDDockerBackend


def clear_singletons(agentConfig):
    get_config_store(agentConfig)._drop()
    get_sd_backend(agentConfig)._drop()


class Response(object):
    """Dummy response class for mocking purpose"""
    def __init__(self, content):
        self.content = content

    def json(self):
        return self.content

    def raise_for_status(self):
        pass


def _get_container_inspect(c_id):
    """Return a mocked container inspect dict from self.container_inspects."""
    for co, _, _, _ in TestServiceDiscovery.container_inspects:
        if co.get('Id') == c_id:
            return co
        return None


def _get_conf_tpls(image_name, trace_config=False):
    """Return a mocked configuration template from self.mock_templates."""
    return copy.deepcopy(TestServiceDiscovery.mock_templates.get(image_name)[0])


def _get_check_tpls(image_name, **kwargs):
    if image_name in TestServiceDiscovery.mock_templates:
        return [copy.deepcopy(TestServiceDiscovery.mock_templates.get(image_name)[0][0][0:3])]
    elif image_name in TestServiceDiscovery.bad_mock_templates:
        try:
            return [copy.deepcopy(TestServiceDiscovery.bad_mock_templates.get(image_name))]
        except Exception:
            return None


def client_read(path):
    """Return a mocked string that would normally be read from a config store (etcd, consul...)."""
    parts = path.split('/')
    config_parts = ['check_names', 'init_configs', 'instances']
    image, config_part = parts[-2], parts[-1]
    return TestServiceDiscovery.mock_tpls.get(image)[0][config_parts.index(config_part)]


class TestServiceDiscovery(unittest.TestCase):
    docker_container_inspect = {
        u'Id': u'69ff25598b2314d1cdb7752cc3a659fb1c1352b32546af4f1454321550e842c0',
        u'Image': u'6ffc02088cb870652eca9ccd4c4fb582f75b29af2879792ed09bb46fd1c898ef',
        u'Name': u'/nginx',
        u'NetworkSettings': {u'IPAddress': u'172.17.0.21', u'Ports': {u'443/tcp': None, u'80/tcp': None}}
    }
    kubernetes_container_inspect = {
        u'Id': u'389dc8a4361f3d6c866e9e9a7b6972b26a31c589c4e2f097375d55656a070bc9',
        u'Image': u'de309495e6c7b2071bc60c0b7e4405b0d65e33e3a4b732ad77615d90452dd827',
        u'Name': u'/k8s_sentinel.38057ab9_redis-master_default_27b84e1e-a81c-11e5-8347-42010af00002_f70875a1',
        u'Config': {u'ExposedPorts': {u'6379/tcp': {}}},
        u'NetworkSettings': {u'IPAddress': u'', u'Ports': None}
    }
    malformed_container_inspect = {
        u'Id': u'69ff25598b2314d1cdb7752cc3a659fb1c1352b32546af4f1454321550e842c0',
        u'Image': u'6ffc02088cb870652eca9ccd4c4fb582f75b29af2879792ed09bb46fd1c898ef',
        u'Name': u'/nginx'
    }
    container_inspects = [
        # (inspect_dict, expected_ip, expected_port)
        (docker_container_inspect, '172.17.0.21', 'port', '443'),
        (kubernetes_container_inspect, None, 'port', '6379'),  # arbitrarily defined in the mocked pod_list
        (malformed_container_inspect, None, 'port', KeyError)
    ]

    # templates with variables already extracted
    mock_templates = {
        # image_name: ([(check_name, init_tpl, instance_tpl, variables)], (expected_config_template))
        'image_0': (
            [('check_0', {}, {'host': '%%host%%'}, ['host'])],
            ('check_0', {}, {'host': '127.0.0.1'})),
        'image_1': (
            [('check_1', {}, {'port': '%%port%%'}, ['port'])],
            ('check_1', {}, {'port': '1337'})),
        'image_2': (
            [('check_2', {}, {'host': '%%host%%', 'port': '%%port%%'}, ['host', 'port'])],
            ('check_2', {}, {'host': '127.0.0.1', 'port': '1337'})),
    }

    # raw templates coming straight from the config store
    mock_tpls = {
        # image_name: ('[check_name]', '[init_tpl]', '[instance_tpl]', expected_python_tpl_list)
        'image_0': (
            ('["check_0"]', '[{}]', '[{"host": "%%host%%"}]'),
            [('check_0', {}, {"host": "%%host%%"})]),
        'image_1': (
            ('["check_1"]', '[{}]', '[{"port": "%%port%%"}]'),
            [('check_1', {}, {"port": "%%port%%"})]),
        'image_2': (
            ('["check_2"]', '[{}]', '[{"host": "%%host%%", "port": "%%port%%"}]'),
            [('check_2', {}, {"host": "%%host%%", "port": "%%port%%"})]),
        'bad_image_0': ((['invalid template']), []),
        'bad_image_1': (('invalid template'), []),
        'bad_image_2': (None, [])
    }

    bad_mock_templates = {
        'bad_image_0': ('invalid template'),
        'bad_image_1': [('invalid template')],
        'bad_image_2': None
    }

    def setUp(self):
        self.etcd_agentConfig = {
            'service_discovery': True,
            'service_discovery_backend': 'docker',
            'sd_template_dir': '/datadog/check_configs',
            'sd_config_backend': 'etcd',
            'sd_backend_host': '127.0.0.1',
            'sd_backend_port': '2380'
        }
        self.consul_agentConfig = {
            'service_discovery': True,
            'service_discovery_backend': 'docker',
            'sd_template_dir': '/datadog/check_configs',
            'sd_config_backend': 'consul',
            'sd_backend_host': '127.0.0.1',
            'sd_backend_port': '8500'
        }
        self.auto_conf_agentConfig = {
            'service_discovery': True,
            'service_discovery_backend': 'docker',
            'sd_template_dir': '/datadog/check_configs',
            'additional_checksd': '/etc/dd-agent/checks.d/',
        }
        self.agentConfigs = [self.etcd_agentConfig, self.consul_agentConfig, self.auto_conf_agentConfig]

    # sd_backend tests

    @mock.patch('utils.http.requests.get')
    @mock.patch('utils.kubeutil.check_yaml')
    def test_get_host_address(self, mock_check_yaml, mock_get):
        kubernetes_config = {'instances': [{'kubelet_port': 1337}]}
        pod_list = {
            'items': [{
                'status': {
                    'podIP': '127.0.0.1',
                    'containerStatuses': [
                        {'containerID': 'docker://389dc8a4361f3d6c866e9e9a7b6972b26a31c589c4e2f097375d55656a070bc9'}
                    ]
                }
            }]
        }

        # (inspect, tpl_var, expected_result)
        ip_address_inspects = [
            ({'NetworkSettings': {}}, 'host', None),
            ({'NetworkSettings': {'IPAddress': ''}}, 'host', None),

            ({'NetworkSettings': {'IPAddress': '127.0.0.1'}}, 'host', '127.0.0.1'),
            ({'NetworkSettings': {'IPAddress': '127.0.0.1', 'Networks': {}}}, 'host', '127.0.0.1'),
            ({'NetworkSettings': {
                'IPAddress': '127.0.0.1',
                'Networks': {'bridge': {'IPAddress': '127.0.0.1'}}}},
             'host', '127.0.0.1'),
            ({'NetworkSettings': {
                'IPAddress': '',
                'Networks': {'bridge': {'IPAddress': '127.0.0.1'}}}},
             'host_bridge', '127.0.0.1'),
            ({'NetworkSettings': {
                'IPAddress': '127.0.0.1',
                'Networks': {
                    'bridge': {'IPAddress': '172.17.0.2'},
                    'foo': {'IPAddress': '192.168.0.2'}}}},
             'host', '127.0.0.1'),

            ({'NetworkSettings': {'Networks': {}}}, 'host', None),
            ({'NetworkSettings': {'Networks': {}}}, 'host_bridge', None),
            ({'NetworkSettings': {'Networks': {'bridge': {}}}}, 'host', None),
            ({'NetworkSettings': {'Networks': {'bridge': {}}}}, 'host_bridge', None),
            ({'NetworkSettings': {
                'Networks': {
                    'bridge': {'IPAddress': '172.17.0.2'}
                }}},
             'host_bridge', '172.17.0.2'),
            ({'NetworkSettings': {
                'Networks': {
                    'bridge': {'IPAddress': '172.17.0.2'},
                    'foo': {'IPAddress': '192.168.0.2'}
                }}},
             'host_foo', '192.168.0.2')
        ]

        mock_check_yaml.return_value = kubernetes_config
        mock_get.return_value = Response(pod_list)

        for c_ins, tpl_var, expected_ip in ip_address_inspects:
            with mock.patch.object(AbstractConfigStore, '__init__', return_value=None):
                with mock.patch('utils.dockerutil.DockerUtil.client', return_value=None):
                    with mock.patch('utils.kubeutil.get_conf_path', return_value=None):
                        sd_backend = get_sd_backend(agentConfig=self.auto_conf_agentConfig)
                        self.assertEquals(sd_backend._get_host_address(c_ins, tpl_var), expected_ip)
                        clear_singletons(self.auto_conf_agentConfig)

    def test_get_port(self):
        with mock.patch('utils.dockerutil.DockerUtil.client', return_value=None):
            for c_ins, _, var_tpl, expected_ports in self.container_inspects:
                sd_backend = get_sd_backend(agentConfig=self.auto_conf_agentConfig)
                if isinstance(expected_ports, str):
                    self.assertEquals(sd_backend._get_port(c_ins, var_tpl), expected_ports)
                else:
                    self.assertRaises(expected_ports, sd_backend._get_port, c_ins, var_tpl)
                clear_singletons(self.auto_conf_agentConfig)

    @mock.patch('docker.Client.inspect_container', side_effect=_get_container_inspect)
    @mock.patch.object(SDDockerBackend, '_get_config_templates', side_effect=_get_conf_tpls)
    def test_get_check_configs(self, mock_inspect_container, mock_get_conf_tpls):
        """Test get_check_config with mocked container inspect and config template"""
        with mock.patch('utils.dockerutil.DockerUtil.client', return_value=None):
            with mock.patch.object(SDDockerBackend, '_get_host_address', return_value='127.0.0.1'):
                with mock.patch.object(SDDockerBackend, '_get_port', return_value='1337'):
                    c_id = self.docker_container_inspect.get('Id')
                    for image in self.mock_templates.keys():
                        sd_backend = get_sd_backend(agentConfig=self.auto_conf_agentConfig)
                        self.assertEquals(
                            sd_backend._get_check_configs(c_id, image)[0],
                            self.mock_templates[image][1])
                        clear_singletons(self.auto_conf_agentConfig)

    @mock.patch.object(AbstractConfigStore, 'get_check_tpls', side_effect=_get_check_tpls)
    def test_get_config_templates(self, mock_get_check_tpls):
        """Test _get_config_templates with mocked get_check_tpls"""
        with mock.patch('utils.dockerutil.DockerUtil.client', return_value=None):
            with mock.patch.object(EtcdStore, 'get_client', return_value=None):
                with mock.patch.object(ConsulStore, 'get_client', return_value=None):
                    for agentConfig in self.agentConfigs:
                        sd_backend = get_sd_backend(agentConfig=agentConfig)
                        # normal cases
                        for image in self.mock_templates.keys():
                            template = sd_backend._get_config_templates(image)
                            expected_template = self.mock_templates.get(image)[0]
                            self.assertEquals(template, expected_template)
                        # error cases
                        for image in self.bad_mock_templates.keys():
                            self.assertEquals(sd_backend._get_config_templates(image), None)
                        clear_singletons(agentConfig)

    def test_render_template(self):
        """Test _render_template"""
        valid_configs = [
            (({}, {'host': '%%host%%'}, {'host': 'foo'}),
             ({}, {'host': 'foo'})),
            (({}, {'host': '%%host%%', 'port': '%%port%%'}, {'host': 'foo', 'port': '1337'}),
             ({}, {'host': 'foo', 'port': '1337'})),
            (({'foo': '%%bar%%'}, {}, {'bar': 'w00t'}),
             ({'foo': 'w00t'}, {})),
            (({'foo': '%%bar%%'}, {'host': '%%host%%'}, {'bar': 'w00t', 'host': 'localhost'}),
             ({'foo': 'w00t'}, {'host': 'localhost'}))
        ]

        invalid_configs = [
            ({}, {'host': '%%host%%'}, {}),  # no value to use
            ({}, {'host': '%%host%%'}, {'port': 42}),  # the variable name doesn't match
            ({'foo': '%%bar%%'}, {'host': '%%host%%'}, {'host': 'foo'})  # not enough value/no matching var name
        ]

        with mock.patch('utils.dockerutil.DockerUtil.client', return_value=None):
            with mock.patch.object(EtcdStore, 'get_client', return_value=None):
                with mock.patch.object(ConsulStore, 'get_client', return_value=None):
                    for agentConfig in self.agentConfigs:
                        sd_backend = get_sd_backend(agentConfig=agentConfig)
                        for tpl, res in valid_configs:
                            init, instance, variables = tpl
                            config = sd_backend._render_template(init, instance, variables)
                            self.assertEquals(config, res)
                        for init, instance, variables in invalid_configs:
                            config = sd_backend._render_template(init, instance, variables)
                            self.assertEquals(config, None)
                            clear_singletons(agentConfig)

    def test_fill_tpl(self):
        """Test _fill_tpl with mocked docker client"""

        valid_configs = [
            # ((inspect, instance_tpl, variables, tags), (expected_instance_tpl, expected_var_values))
            (({}, {'host': 'localhost'}, [], None), ({'host': 'localhost'}, {})),
            (
                ({'NetworkSettings': {'IPAddress': ''}}, {'host': 'localhost'}, [], None),
                ({'host': 'localhost'}, {})
            ),
            (
                ({'NetworkSettings': {'Networks': {}}}, {'host': 'localhost'}, [], None),
                ({'host': 'localhost'}, {})
            ),
            (
                ({'NetworkSettings': {'Networks': {'bridge': {}}}}, {'host': 'localhost'}, [], None),
                ({'host': 'localhost'}, {})
            ),
            (
                ({'NetworkSettings': {'IPAddress': '127.0.0.1'}},
                 {'host': '%%host%%', 'port': 1337}, ['host'], ['foo', 'bar:baz']),
                ({'host': '%%host%%', 'port': 1337, 'tags': ['foo', 'bar:baz']}, {'host': '127.0.0.1'}),
            ),
            (
                ({'NetworkSettings': {'IPAddress': '127.0.0.1', 'Networks': {}}},
                 {'host': '%%host%%', 'port': 1337}, ['host'], ['foo', 'bar:baz']),
                ({'host': '%%host%%', 'port': 1337, 'tags': ['foo', 'bar:baz']}, {'host': '127.0.0.1'}),
            ),
            (
                ({'NetworkSettings': {
                    'IPAddress': '127.0.0.1',
                    'Networks': {'bridge': {'IPAddress': '172.17.0.2'}}}
                  },
                 {'host': '%%host%%', 'port': 1337}, ['host'], ['foo', 'bar:baz']),
                ({'host': '%%host%%', 'port': 1337, 'tags': ['foo', 'bar:baz']}, {'host': '127.0.0.1'}),
            ),
            (
                ({'NetworkSettings': {
                    'IPAddress': '',
                    'Networks': {
                        'bridge': {'IPAddress': '172.17.0.2'},
                        'foo': {'IPAddress': '192.168.0.2'}
                    }}
                  },
                 {'host': '%%host_bridge%%', 'port': 1337}, ['host_bridge'], ['foo', 'bar:baz']),
                ({'host': '%%host_bridge%%', 'port': 1337, 'tags': ['foo', 'bar:baz']},
                 {'host_bridge': '172.17.0.2'}),
            ),
            (
                ({'NetworkSettings': {
                    'IPAddress': '',
                    'Networks': {
                        'bridge': {'IPAddress': '172.17.0.2'},
                        'foo': {'IPAddress': '192.168.0.2'}
                    }}
                  },
                 {'host': '%%host_foo%%', 'port': 1337}, ['host_foo'], ['foo', 'bar:baz']),
                ({'host': '%%host_foo%%', 'port': 1337, 'tags': ['foo', 'bar:baz']},
                 {'host_foo': '192.168.0.2'}),
            ),
            (
                ({'NetworkSettings': {'IPAddress': '127.0.0.1', 'Ports': {'42/tcp': None, '22/tcp': None}}},
                 {'host': '%%host%%', 'port': '%%port_1%%', 'tags': ['env:test']},
                 ['host', 'port_1'], ['foo', 'bar:baz']),
                ({'host': '%%host%%', 'port': '%%port_1%%', 'tags': ['env:test', 'foo', 'bar:baz']},
                 {'host': '127.0.0.1', 'port_1': '42'})
            )
        ]

        # should not fail but return something specific
        edge_cases = [
            # ((inspect, instance_tpl, variables, tags), (expected_instance_tpl, expected_var_values))

            # specify bridge but there is also a default IPAddress (networks should be preferred)
            (
                ({'NetworkSettings': {
                    'IPAddress': '127.0.0.1',
                    'Networks': {'bridge': {'IPAddress': '172.17.0.2'}}}},
                 {'host': '%%host_bridge%%', 'port': 1337}, ['host_bridge'], ['foo', 'bar:baz']),
                ({'host': '%%host_bridge%%', 'port': 1337, 'tags': ['foo', 'bar:baz']},
                 {'host_bridge': '172.17.0.2'})
            ),
            # specify index but there is a default IPAddress (there's a specifier, even if it's wrong, walking networks should be preferred)
            (
                ({'NetworkSettings': {
                    'IPAddress': '127.0.0.1',
                    'Networks': {'bridge': {'IPAddress': '172.17.0.2'}}}},
                 {'host': '%%host_0%%', 'port': 1337}, ['host_0'], ['foo', 'bar:baz']),
                ({'host': '%%host_0%%', 'port': 1337, 'tags': ['foo', 'bar:baz']}, {'host_0': '172.17.0.2'}),
            ),
            # missing key for host, bridge network should be preferred
            (
                ({'NetworkSettings': {'Networks': {
                    'bridge': {'IPAddress': '127.0.0.1'},
                    'foo': {'IPAddress': '172.17.0.2'}}}},
                 {'host': '%%host_bar%%', 'port': 1337}, ['host_bar'], []),
                ({'host': '%%host_bar%%', 'port': 1337}, {'host_bar': '127.0.0.1'}),
            ),
            # missing index for port
            (
                ({'NetworkSettings': {'IPAddress': '127.0.0.1', 'Ports': {'42/tcp': None, '22/tcp': None}}},
                 {'host': '%%host%%', 'port': '%%port_2%%', 'tags': ['env:test']},
                 ['host', 'port_2'], ['foo', 'bar:baz']),
                ({'host': '%%host%%', 'port': '%%port_2%%', 'tags': ['env:test', 'foo', 'bar:baz']},
                 {'host': '127.0.0.1', 'port_2': '42'})
            )
        ]

        # should raise
        invalid_config = [
            # ((inspect, instance_tpl, variables, tags), expected_exception)

            # template variable but no IPAddress available
            (
                ({'NetworkSettings': {'Networks': {}}},
                 {'host': '%%host%%', 'port': 1337}, ['host'], ['foo', 'bar:baz']),
                Exception,
            ),
            # index but no IPAddress available
            (
                ({'NetworkSettings': {'Networks': {}}},
                 {'host': '%%host_0%%', 'port': 1337}, ['host_0'], ['foo', 'bar:baz']),
                Exception,
            ),
            # key but no IPAddress available
            (
                ({'NetworkSettings': {'Networks': {}}},
                 {'host': '%%host_foo%%', 'port': 1337}, ['host_foo'], ['foo', 'bar:baz']),
                Exception,
            ),

            # template variable but no port available
            (
                ({'NetworkSettings': {'Networks': {}}},
                 {'host': 'localhost', 'port': '%%port%%'}, ['port'], []),
                Exception,
            ),
            # index but no port available
            (
                ({'NetworkSettings': {'Networks': {}}},
                 {'host': 'localhost', 'port_0': '%%port%%'}, ['port_0'], []),
                Exception,
            ),
            # key but no port available
            (
                ({'NetworkSettings': {'Networks': {}}},
                 {'host': 'localhost', 'port': '%%port_foo%%'}, ['port_foo'], []),
                Exception,
            )
        ]

        with mock.patch('utils.dockerutil.DockerUtil.client', return_value=None):
            with mock.patch.object(EtcdStore, 'get_client', return_value=None):
                with mock.patch.object(ConsulStore, 'get_client', return_value=None):
                    for ac in self.agentConfigs:
                        sd_backend = get_sd_backend(agentConfig=ac)
                        try:
                            for co in valid_configs + edge_cases:
                                inspect, tpl, variables, tags = co[0]
                                instance_tpl, var_values = sd_backend._fill_tpl(inspect, tpl, variables, tags)
                                for key in instance_tpl.keys():
                                    if isinstance(instance_tpl[key], list):
                                        self.assertEquals(len(instance_tpl[key]), len(co[1][0].get(key)))
                                        for elem in instance_tpl[key]:
                                            self.assertTrue(elem in co[1][0].get(key))
                                    else:
                                        self.assertEquals(instance_tpl[key], co[1][0].get(key))
                                self.assertEquals(var_values, co[1][1])

                            for co in invalid_config:
                                inspect, tpl, variables, tags = co[0]
                                self.assertRaises(co[1], sd_backend._fill_tpl(inspect, tpl, variables, tags))

                            clear_singletons(ac)
                        except Exception:
                            clear_singletons(ac)
                            raise

    # config_stores tests

    def test_get_auto_config(self):
        """Test _get_auto_config"""
        expected_tpl = {
            'redis': ('redisdb', None, {"host": "%%host%%", "port": "%%port%%"}),
            'consul': ('consul', None, {
                "url": "http://%%host%%:%%port%%", "catalog_checks": True, "new_leader_checks": True
            }),
            'foobar': None
        }

        config_store = get_config_store(self.auto_conf_agentConfig)
        for image in expected_tpl.keys():
            config = config_store._get_auto_config(image)
            self.assertEquals(config, expected_tpl.get(image))

    @mock.patch.object(AbstractConfigStore, 'client_read', side_effect=client_read)
    def test_get_check_tpls(self, mock_client_read):
        """Test get_check_tpls"""
        valid_config = ['image_0', 'image_1', 'image_2']
        invalid_config = ['bad_image_0', 'bad_image_1']
        config_store = get_config_store(self.auto_conf_agentConfig)
        for image in valid_config:
            tpl = self.mock_tpls.get(image)[1]
            self.assertEquals(tpl, config_store.get_check_tpls(image))
        for image in invalid_config:
            tpl = self.mock_tpls.get(image)[1]
            self.assertEquals(tpl, config_store.get_check_tpls(image))
