import unittest
from nose.plugins.attrib import attr

from tests.common import load_check, read_data_from_file

@attr(requires='nginx')
class TestNginx(unittest.TestCase):

    def setUp(self):
        self.agent_config = {
            'version': '0.1',
            'api_key': 'toto'
        }
        self.config = {
            'instances': [
                {'nginx_status_url': 'http://localhost:44441/nginx_status/'},
                {
                    'nginx_status_url': 'http://localhost:44441/nginx_status/',
                    'tags': ['first_one'],
                },
                {
                    'nginx_status_url': 'http://dummyurl:44441/nginx_status/',
                    'tags': ['dummy'],
                },
                {
                    'nginx_status_url': 'http://localhost:44441/nginx_status/',
                    'tags': ['second'],
                },
            ]
        }


    def test_nginx(self):
        nginx = load_check('nginx', self.config, self.agent_config)
        nginx.check(self.config['instances'][0])
        r = nginx.get_metrics()
        self.assertEquals(len([t for t in r if t[0] == "nginx.net.connections"]), 1, r)

        nginx.check(self.config['instances'][1])
        r = nginx.get_metrics()
        self.assertEquals(r[0][3].get('tags'), ['first_one'])
        service_checks = nginx.get_service_checks()
        can_connect = [sc for sc in service_checks if sc['check'] == 'nginx.can_connect']
        for i in range(len(can_connect)):
            self.assertEquals(set(can_connect[i]['tags']), set(['host:localhost', 'port:44441']), service_checks)

    def test_nginx_plus(self):
        test_data = read_data_from_file('nginx_plus_in.json')
        expected = eval(read_data_from_file('nginx_plus_out.python'))
        nginx = load_check('nginx', self.config, self.agent_config)
        parsed = nginx.parse_json(test_data)
        parsed.sort()
        self.assertEquals(parsed, expected)
