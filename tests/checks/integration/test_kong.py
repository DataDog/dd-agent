# stdlib
import unittest

# 3p
from nose.plugins.attrib import attr

# project
from tests.checks.common import load_check


@attr(requires='kong')
class TestKong(unittest.TestCase):

    def setUp(self):
        self.agent_config = {
            'version': '0.1',
            'api_key': 'toto'
        }
        self.config = {
            'instances': [
                {'kong_status_url': 'http://localhost:8001/status/'},
                {
                    'kong_status_url': 'http://localhost:8001/status/',
                    'tags': ['first_one'],
                }
            ]
        }

    def test_kong_one_connection(self):
        kong = load_check('kong', self.config, self.agent_config)
        kong.check(self.config['instances'][0])
        r = kong.get_metrics()
        self.assertEquals(len([t for t in r if t[0] == "kong.server.connections_active"]), 1, r)

    def test_kong_tags(self):
        kong = load_check('kong', self.config, self.agent_config)
        kong.check(self.config['instances'][1])
        r = kong.get_metrics()
        self.assertEquals(r[0][3].get('tags')[0], 'first_one')
        service_checks = kong.get_service_checks()
        can_connect = [sc for sc in service_checks if sc['check'] == 'kong.can_connect']
        for i in range(len(can_connect)):
            self.assertEquals(set(can_connect[i]['tags']), set(['host:localhost', 'port:8001']), service_checks)
