# stdlib
import copy
import mock
import os
import unittest
from collections import defaultdict

# 3p
from nose.plugins.attrib import attr

# project
from config import generate_jmx_configs
from utils.service_discovery.config_stores import get_config_store
from utils.service_discovery.consul_config_store import ConsulStore
from utils.service_discovery.etcd_config_store import EtcdStore
from utils.service_discovery.abstract_config_store import AbstractConfigStore, \
    _TemplateCache, CONFIG_FROM_KUBE, CONFIG_FROM_TEMPLATE, CONFIG_FROM_AUTOCONF, CONFIG_FROM_LABELS
from utils.service_discovery.sd_backend import get_sd_backend
from utils.service_discovery.sd_docker_backend import SDDockerBackend, _SDDockerBackendConfigFetchState
from utils.dockerutil import DockerUtil


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
    for co, _, _, _, _, _ in TestServiceDiscovery.container_inspects:
        if co.get('Id') == c_id:
            return co
        return None


def _get_conf_tpls(image_name, kube_annotations=None, kube_pod_name=None, kube_container_name=None):
    """Return a mocked configuration template from self.mock_templates."""
    return [(x, y) for x, y in
            copy.deepcopy(TestServiceDiscovery.mock_templates.get(image_name)[0])]


def _get_check_tpls(image_name, **kwargs):
    if image_name in TestServiceDiscovery.mock_templates:
        result = copy.deepcopy(TestServiceDiscovery.mock_templates.get(image_name)[0][0])
        return [(result[0], result[1][0:3])]
    elif image_name in TestServiceDiscovery.bad_mock_templates:
        try:
            return [copy.deepcopy(TestServiceDiscovery.bad_mock_templates.get(image_name))]
        except Exception:
            return None


def client_read(path, **kwargs):
    """Return a mocked string that would normally be read from a config store (etcd, consul...)."""
    parts = path.split('/')
    config_parts = ['check_names', 'init_configs', 'instances']
    image, config_part = parts[-2], parts[-1]
    if 'all' in kwargs:
        return {}
    else:
        return TestServiceDiscovery.mock_raw_templates.get(image)[0][config_parts.index(config_part)]


def issue_read(identifier):
    return TestServiceDiscovery.mock_raw_templates.get(identifier)

@attr('unix')
class TestServiceDiscovery(unittest.TestCase):
    docker_container_inspect = {
        u'Id': u'69ff25598b2314d1cdb7752cc3a659fb1c1352b32546af4f1454321550e842c0',
        u'Image': u'nginx',
        u'Name': u'/nginx',
        u'NetworkSettings': {u'IPAddress': u'172.17.0.21', u'Ports': {u'443/tcp': None, u'80/tcp': None}},
        u'State': {u'Pid': 1234}
    }
    docker_container_inspect_with_label = {
        u'Id': u'69ff25598b2314d1cdb7752cc3a659fb1c1352b32546af4f1454321550e842c0',
        u'Image': u'nginx',
        u'Name': u'/nginx',
        u'NetworkSettings': {u'IPAddress': u'172.17.0.21', u'Ports': {u'443/tcp': None, u'80/tcp': None}},
        u'Config': {'Labels': {'com.datadoghq.sd.check.id': 'custom-nginx'}}
    }
    kubernetes_container_inspect = {
        u'Id': u'389dc8a4361f3d6c866e9e9a7b6972b26a31c589c4e2f097375d55656a070bc9',
        u'Image': u'foo',
        u'Name': u'/k8s_sentinel.38057ab9_redis-master_default_27b84e1e-a81c-11e5-8347-42010af00002_f70875a1',
        u'Config': {u'ExposedPorts': {u'6379/tcp': {}}},
        u'NetworkSettings': {u'IPAddress': u'', u'Ports': None}
    }
    malformed_container_inspect = {
        u'Id': u'69ff25598b2314d1cdb7752cc3a659fb1c1352b32546af4f1454321550e842c0',
        u'Image': u'foo',
        u'Name': u'/nginx'
    }
    container_inspects = [
        # (inspect_dict, expected_ip, tpl_var, expected_port, expected_ident, expected_id, expected_pid)
        (docker_container_inspect, '172.17.0.21', 'port', '443', 'nginx', '1234'),
        (docker_container_inspect_with_label, '172.17.0.21', 'port', '443', 'custom-nginx', None),
        (kubernetes_container_inspect, None, 'port', '6379', 'foo', None),  # arbitrarily defined in the mocked pod_list
        (malformed_container_inspect, None, 'port', KeyError, 'foo', None)
    ]

    # templates with variables already extracted
    mock_templates = {
        # image_name: ([(source, (check_name, init_tpl, instance_tpl, variables))], (expected_config_template))
        'image_0': (
            [('template', ('check_0', {}, {'host': '%%host%%'}, ['host']))],
            ('template', ('check_0', {}, [{'host': '127.0.0.1', 'tags': [u'docker_image:nginx', u'image_name:nginx']}]))),
        'image_1': (
            [('template', ('check_1', {}, {'port': '%%port%%'}, ['port']))],
            ('template', ('check_1', {}, [{'port': '1337', 'tags': [u'docker_image:nginx', u'image_name:nginx']}]))),
        'image_2': (
            [('template', ('check_2', {}, {'host': '%%host%%', 'port': '%%port%%'}, ['host', 'port']))],
            ('template', ('check_2', {}, [{'host': '127.0.0.1', 'port': '1337', 'tags': [u'docker_image:nginx', u'image_name:nginx']}]))),
        'image_3': (
            [('template', ('check_3', {}, [{'host': '%%host%%', 'port': '%%port%%'}, {"foo": "%%host%%", "bar": "%%port%%"}], ['host', 'port', 'host', 'port']))],
            ('template', ('check_3', {}, [
                {'host': '127.0.0.1', 'port': '1337', 'tags': [u'docker_image:nginx', u'image_name:nginx']},
                {'foo': '127.0.0.1', 'bar': '1337', 'tags': [u'docker_image:nginx', u'image_name:nginx']}]))),
    }

    # raw templates coming straight from the config store
    mock_raw_templates = {
        # image_name: ('[check_name]', '[init_tpl]', '[instance_tpl]', expected_python_tpl_list)
        'image_0': (
            ('["check_0"]', '[{}]', '[{"host": "%%host%%"}]'),
            [('template', ('check_0', {}, {"host": "%%host%%"}))]),
        'image_1': (
            ('["check_1"]', '[{}]', '[{"port": "%%port%%"}]'),
            [('template', ('check_1', {}, {"port": "%%port%%"}))]),
        'image_2': (
            ('["check_2"]', '[{}]', '[{"host": "%%host%%", "port": "%%port%%"}]'),
            [('template', ('check_2', {}, {"host": "%%host%%", "port": "%%port%%"}))]),
        'image_3': (
            ('["check_3"]', '[{}]', '[[{"host": "%%host%%", "port": "%%port%%"},{"foo": "%%host%%", "bar": "%%port%%"}]]'),
            [('template', ('check_3', {}, [{"host": "%%host%%", "port": "%%port%%"}, {"foo": "%%host%%", "bar": "%%port%%"}]))]),
        # multi-checks environment
        'image_4': (
            ('["check_4a", "check_4b"]', '[{},{}]', '[[{"host": "%%host%%", "port": "%%port%%"}],[{"foo": "%%host%%", "bar": "%%port%%"}]]'),
            [('template', ('check_4a', {}, [{"host": "%%host%%", "port": "%%port%%"}])), ('template', ('check_4b', {}, [{"foo": "%%host%%", "bar": "%%port%%"}]))]),
        'bad_image_0': ((['invalid template']), []),
        'bad_image_1': (('invalid template'), []),
        'bad_image_2': (None, []),
        'nginx': ('["nginx"]', '[{}]', '[{"host": "localhost"}]'),
        'nginx:latest': ('["nginx"]', '[{}]', '[{"host": "localhost", "tags": ["foo"]}]'),
        'custom-nginx': ('["nginx"]', '[{}]', '[{"host": "localhost"}]'),
        'repo/custom-nginx': ('["nginx"]', '[{}]', '[{"host": "localhost", "tags": ["bar"]}]'),
        'repo/dir:5000/custom-nginx:latest': ('["nginx"]', '[{}]', '[{"host": "local", "tags": ["foobar"]}]')
    }

    bad_mock_templates = {
        'bad_image_0': ('invalid template'),
        'bad_image_1': [('invalid template')],
        'bad_image_2': None
    }

    jmx_sd_configs = {
        'tomcat': ('auto-configuration', ({}, [{"host": "localhost", "port": "9012"}])),
        'solr': ('auto-configuration', ({}, [
            {"host": "localhost", "port": "9999", "username": "foo", "password": "bar"},
            {"host": "remotehost", "port": "5555", "username": "haz", "password": "bar"},
        ])),
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
    @mock.patch('utils.kubernetes.kubeutil.check_yaml')
    @mock.patch.object(AbstractConfigStore, '__init__', return_value=None)
    @mock.patch('utils.dockerutil.DockerUtil.client', return_value=None)
    @mock.patch('utils.kubernetes.kubeutil.get_conf_path', return_value=None)
    def test_get_host_address(self, mock_check_yaml, mock_get, *args):
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
             'host', '172.17.0.2'),

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
            state = _SDDockerBackendConfigFetchState(lambda _: c_ins)
            sd_backend = get_sd_backend(agentConfig=self.auto_conf_agentConfig)
            self.assertEquals(sd_backend._get_host_address(state, 'container id', tpl_var), expected_ip)
            clear_singletons(self.auto_conf_agentConfig)

    @mock.patch('config.get_auto_confd_path', return_value=os.path.join(
        os.path.dirname(__file__), 'fixtures/auto_conf/'))
    @mock.patch('utils.dockerutil.DockerUtil.client', return_value=None)
    def test_get_port(self, *args):
        for c_ins, _, var_tpl, expected_ports, _, _ in self.container_inspects:
            state = _SDDockerBackendConfigFetchState(lambda _: c_ins)
            sd_backend = get_sd_backend(agentConfig=self.auto_conf_agentConfig)
            if isinstance(expected_ports, str):
                self.assertEquals(sd_backend._get_port(state, 'container id', var_tpl), expected_ports)
            else:
                self.assertRaises(expected_ports, sd_backend._get_port, state, 'c_id', var_tpl)
            clear_singletons(self.auto_conf_agentConfig)

    @mock.patch('config.get_auto_confd_path', return_value=os.path.join(
        os.path.dirname(__file__), 'fixtures/auto_conf/'))
    @mock.patch('utils.dockerutil.DockerUtil.client', return_value=None)
    def test_get_container_pid(self, *args):
        for c_ins, _, var_tpl, _, _, expected_pid in self.container_inspects:
            state = _SDDockerBackendConfigFetchState(lambda _: c_ins)
            sd_backend = get_sd_backend(agentConfig=self.auto_conf_agentConfig)
            self.assertEquals(sd_backend._get_container_pid(state, 'container id', var_tpl), expected_pid)
            clear_singletons(self.auto_conf_agentConfig)

    @mock.patch('config.get_auto_confd_path', return_value=os.path.join(
        os.path.dirname(__file__), 'fixtures/auto_conf/'))
    @mock.patch('utils.dockerutil.DockerUtil.client', return_value=None)
    @mock.patch.object(SDDockerBackend, '_get_host_address', return_value='127.0.0.1')
    @mock.patch.object(SDDockerBackend, '_get_port', return_value='1337')
    @mock.patch.object(SDDockerBackend, '_get_config_templates', side_effect=_get_conf_tpls)
    def test_get_check_configs(self, *args):
        """Test get_check_config with mocked container inspect and config template"""
        c_id = self.docker_container_inspect.get('Id')
        for image in self.mock_templates.keys():
            sd_backend = get_sd_backend(agentConfig=self.auto_conf_agentConfig)
            state = _SDDockerBackendConfigFetchState(_get_container_inspect)
            self.assertEquals(
                sd_backend._get_check_configs(state, c_id, image)[0],
                self.mock_templates[image][1])
            clear_singletons(self.auto_conf_agentConfig)

    @mock.patch('config.get_auto_confd_path', return_value=os.path.join(
        os.path.dirname(__file__), 'fixtures/auto_conf/'))
    @mock.patch('utils.dockerutil.DockerUtil.client', return_value=None)
    @mock.patch.object(ConsulStore, 'get_client', return_value=None)
    @mock.patch.object(EtcdStore, 'get_client', return_value=None)
    @mock.patch.object(AbstractConfigStore, 'get_check_tpls', side_effect=_get_check_tpls)
    def test_get_config_templates(self, *args):
        """Test _get_config_templates with mocked get_check_tpls"""
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

    @mock.patch('config.get_auto_confd_path', return_value=os.path.join(
        os.path.dirname(__file__), 'fixtures/auto_conf/'))
    def test_render_template(self, mock_get_auto_confd_path):
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

    @mock.patch('config.get_auto_confd_path', return_value=os.path.join(
        os.path.dirname(__file__), 'fixtures/auto_conf/'))
    @mock.patch('utils.dockerutil.DockerUtil.client', return_value=None)
    @mock.patch.object(EtcdStore, 'get_client', return_value=None)
    @mock.patch.object(ConsulStore, 'get_client', return_value=None)
    def test_fill_tpl(self, *args):
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
                ({'host': '%%host%%', 'port': 1337, 'tags': ['foo', 'bar:baz']}, {'host': '172.17.0.2'}),
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
            ),
            (
                ({'NetworkSettings': {'IPAddress': '127.0.0.1', 'Ports': {'42/tcp': None, '22/tcp': None}}},
                 {'host': '%%host%%', 'port': '%%port_1%%', 'tags': {'env': 'test'}},
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

        for ac in self.agentConfigs:
            sd_backend = get_sd_backend(agentConfig=ac)
            try:
                for co in valid_configs + edge_cases:
                    inspect, tpl, variables, tags = co[0]
                    state = _SDDockerBackendConfigFetchState(lambda _: inspect)
                    instance_tpl, var_values = sd_backend._fill_tpl(state, 'c_id', tpl, variables, tags)
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
                    state = _SDDockerBackendConfigFetchState(lambda _: inspect)
                    self.assertRaises(co[1], sd_backend._fill_tpl(state, 'c_id', tpl, variables, tags))
            finally:
                clear_singletons(ac)

    # config_stores tests

    @mock.patch('config.get_auto_confd_path', return_value=os.path.join(
        os.path.dirname(__file__), 'fixtures/auto_conf/'))
    def test_get_auto_config(self, mock_get_auto_confd_path):
        """Test _get_auto_config"""
        expected_tpl = {
            'disk': [('disk', None, {"host": "%%host%%", "port": "%%port%%"})],
            'consul': [('consul', None, {
                        "url": "http://%%host%%:%%port%%", "catalog_checks": True, "new_leader_checks": True
                        })],
            'disk:v1': [('disk', None, {"host": "%%host%%", "port": "%%port%%"})],
            'foobar': []
        }
        config_store = get_config_store(self.auto_conf_agentConfig)
        for image in expected_tpl.keys():
            config = config_store._get_auto_config(image)
            self.assertEquals(config, expected_tpl.get(image))

    @mock.patch('config.get_auto_confd_path', return_value=os.path.join(
        os.path.dirname(__file__), 'fixtures/auto_conf/'))
    @mock.patch.object(AbstractConfigStore, 'client_read', side_effect=client_read)
    def test_get_check_tpls(self, *args):
        """Test get_check_tpls"""
        valid_config = ['image_0', 'image_1', 'image_2']
        invalid_config = ['bad_image_0', 'bad_image_1']
        config_store = get_config_store(self.auto_conf_agentConfig)
        for image in valid_config:
            tpl = self.mock_raw_templates.get(image)[1]
            self.assertEquals(tpl, config_store.get_check_tpls(image))
        for image in invalid_config:
            tpl = self.mock_raw_templates.get(image)[1]
            self.assertEquals(tpl, config_store.get_check_tpls(image))

    @mock.patch('config.get_auto_confd_path', return_value=os.path.join(
        os.path.dirname(__file__), 'fixtures/auto_conf/'))
    @mock.patch.object(AbstractConfigStore, 'client_read', side_effect=client_read)
    def test_get_check_tpls_kube(self, *args):
        """Test get_check_tpls for kubernetes annotations"""
        valid_config = ['image_0', 'image_1', 'image_2', 'image_3', 'image_4']
        invalid_config = ['bad_image_0']
        config_store = get_config_store(self.auto_conf_agentConfig)
        for image in valid_config + invalid_config:
            tpl = self.mock_raw_templates.get(image)[1]
            tpl = [(CONFIG_FROM_KUBE, t[1]) for t in tpl]
            if tpl:
                self.assertNotEquals(
                    tpl,
                    config_store.get_check_tpls('k8s-' + image, auto_conf=True))
            self.assertEquals(
                tpl,
                config_store.get_check_tpls(
                    'k8s-' + image, auto_conf=True,
                    kube_pod_name=image,
                    kube_container_name='foo',
                    kube_annotations=dict(zip(
                        ['service-discovery.datadoghq.com/foo.check_names',
                         'service-discovery.datadoghq.com/foo.init_configs',
                         'service-discovery.datadoghq.com/foo.instances'],
                        self.mock_raw_templates[image][0]))))

    @mock.patch('config.get_auto_confd_path', return_value=os.path.join(
        os.path.dirname(__file__), 'fixtures/auto_conf/'))
    @mock.patch.object(AbstractConfigStore, 'client_read', side_effect=client_read)
    def test_get_check_tpls_labels(self, *args):
        """Test get_check_tpls from docker labesl"""
        valid_config = ['image_0', 'image_1', 'image_2', 'image_3', 'image_4']
        invalid_config = ['bad_image_0']
        config_store = get_config_store(self.auto_conf_agentConfig)
        for image in valid_config + invalid_config:
            tpl = self.mock_raw_templates.get(image)[1]
            tpl = [(CONFIG_FROM_LABELS, t[1]) for t in tpl]
            if tpl:
                self.assertNotEquals(
                    tpl,
                    config_store.get_check_tpls(image, auto_conf=True))
            self.assertEquals(
                tpl,
                config_store.get_check_tpls(
                    image, auto_conf=True,
                    docker_labels=dict(zip(
                        ['service-discovery.datadoghq.com/check_names',
                         'service-discovery.datadoghq.com/init_configs',
                         'service-discovery.datadoghq.com/instances'],
                        self.mock_raw_templates[image][0]))))

    @mock.patch('config.get_auto_confd_path', return_value=os.path.join(
        os.path.dirname(__file__), 'fixtures/auto_conf/'))
    def test_get_config_id(self, mock_get_auto_confd_path):
        """Test get_config_id"""
        with mock.patch('utils.dockerutil.DockerUtil.client', return_value=None):
            for c_ins, _, _, _, expected_ident, _ in self.container_inspects:
                sd_backend = get_sd_backend(agentConfig=self.auto_conf_agentConfig)
                self.assertEqual(
                    sd_backend.get_config_id(DockerUtil().image_name_extractor(c_ins), c_ins.get('Config', {}).get('Labels', {})),
                    expected_ident)
                clear_singletons(self.auto_conf_agentConfig)

    @mock.patch('config.get_auto_confd_path', return_value=os.path.join(
        os.path.dirname(__file__), 'fixtures/auto_conf/'))
    @mock.patch.object(_TemplateCache, '_issue_read', side_effect=issue_read)
    def test_read_config_from_store(self, *args):
        """Test read_config_from_store"""
        valid_idents = [('nginx', 'nginx'), ('nginx:latest', 'nginx:latest'),
                        ('custom-nginx', 'custom-nginx'), ('custom-nginx:latest', 'custom-nginx'),
                        ('repo/custom-nginx:latest', 'custom-nginx'),
                        ('repo/dir:5000/custom-nginx:latest', 'repo/dir:5000/custom-nginx:latest')]
        invalid_idents = ['foo']
        config_store = get_config_store(self.auto_conf_agentConfig)
        for ident, expected_key in valid_idents:
            tpl = config_store.read_config_from_store(ident)
            # source is added after reading from the store
            self.assertEquals(
                tpl,
                {
                    CONFIG_FROM_AUTOCONF: None,
                    CONFIG_FROM_TEMPLATE: self.mock_raw_templates.get(expected_key)
                }
            )
        for ident in invalid_idents:
            self.assertEquals(config_store.read_config_from_store(ident), [])

    @mock.patch('config.get_auto_confd_path', return_value=os.path.join(
        os.path.dirname(__file__), 'fixtures/auto_conf/'))
    @mock.patch('utils.dockerutil.DockerUtil.client', return_value=None)
    @mock.patch.object(SDDockerBackend, 'get_configs', return_value=jmx_sd_configs)
    def test_read_jmx_config_from_store(self, *args):
        """Test JMX configs are read and converted to YAML"""
        jmx_configs = generate_jmx_configs(self.auto_conf_agentConfig, "jmxhost")
        valid_configs = {
            'solr_0': "init_config: {}\ninstances:\n- host: localhost\n  password: bar\n  "
            "port: '9999'\n  username: foo\n- host: remotehost\n  password: bar\n  "
            "port: '5555'\n  username: haz\n",
            'tomcat_0': "init_config: {}\ninstances:\n- host: localhost\n  port: '9012'\n"
        }
        for check in self.jmx_sd_configs:
            key = '{}_0'.format(check)
            self.assertEquals(jmx_configs[key], valid_configs[key])

    # Template cache
    @mock.patch('utils.service_discovery.abstract_config_store.get_auto_conf_images')
    def test_populate_auto_conf(self, mock_get_auto_conf_images):
        """test _populate_auto_conf"""
        auto_tpls = {
            'foo': [['check0', 'check1'], [{}, {}], [{}, {}]],
            'bar': [['check2', 'check3', 'check3'], [{}, {}, {}], [{}, {'foo': 'bar'}, {'bar': 'foo'}]],
        }
        cache = _TemplateCache(issue_read, '')
        cache.auto_conf_templates = defaultdict(lambda: [[]] * 3)
        mock_get_auto_conf_images.return_value = auto_tpls

        cache._populate_auto_conf()
        self.assertEquals(cache.auto_conf_templates['foo'], auto_tpls['foo'])
        self.assertEquals(cache.auto_conf_templates['bar'],
            [['check2', 'check3'], [{}, {}], [{}, {'foo': 'bar'}]])

    @mock.patch('config.get_auto_confd_path', return_value=os.path.join(
        os.path.dirname(__file__), 'fixtures/auto_conf/'))
    @mock.patch.object(_TemplateCache, '_issue_read', return_value=None)
    def test_get_templates(self, *args):
        """test get_templates"""
        kv_tpls = {
            'foo': [['check0', 'check1'], [{}, {}], [{}, {}]],
            'bar': [['check2', 'check3'], [{}, {}], [{}, {}]],
        }
        auto_tpls = {
            'foo': [['check3', 'check5'], [{}, {}], [{}, {}]],
            'bar': [['check2', 'check6'], [{}, {}], [{}, {}]],
            'foobar': [['check4'], [{}], [{}]],
        }
        cache = _TemplateCache(issue_read, '')
        cache.kv_templates = kv_tpls
        cache.auto_conf_templates = auto_tpls
        self.assertEquals(cache.get_templates('foo'),
            {CONFIG_FROM_TEMPLATE: [['check0', 'check1'], [{}, {}], [{}, {}]],
                CONFIG_FROM_AUTOCONF: [['check3', 'check5'], [{}, {}], [{}, {}]]}
        )

        self.assertEquals(cache.get_templates('bar'),
            # check3 must come from template not autoconf
            {CONFIG_FROM_TEMPLATE: [['check2', 'check3'], [{}, {}], [{}, {}]],
                CONFIG_FROM_AUTOCONF: [['check6'], [{}], [{}]]}
        )

        self.assertEquals(cache.get_templates('foobar'),
            {CONFIG_FROM_TEMPLATE: None,
                CONFIG_FROM_AUTOCONF: [['check4'], [{}], [{}]]}
        )

        self.assertEquals(cache.get_templates('baz'), None)

    @mock.patch('config.get_auto_confd_path', return_value=os.path.join(
        os.path.dirname(__file__), 'fixtures/auto_conf/'))
    def test_get_check_names(self, mock_get_auto_confd_path):
        """Test get_check_names"""
        kv_tpls = {
            'foo': [['check0', 'check1'], [{}, {}], [{}, {}]],
            'bar': [['check2', 'check3'], [{}, {}], [{}, {}]],
        }
        auto_tpls = {
            'foo': [['check4', 'check5'], [{}, {}], [{}, {}]],
            'bar': [['check2', 'check6'], [{}, {}], [{}, {}]],
            'foobar': None,
        }
        cache = _TemplateCache(issue_read, '')
        cache.kv_templates = kv_tpls
        cache.auto_conf_templates = auto_tpls
        self.assertEquals(cache.get_check_names('foo'), set(['check0', 'check1', 'check4', 'check5']))
        self.assertEquals(cache.get_check_names('bar'), set(['check2', 'check3', 'check6']))
        self.assertEquals(cache.get_check_names('foobar'), set())
        self.assertEquals(cache.get_check_names('baz'), set())
