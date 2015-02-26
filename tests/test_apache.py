import unittest
from nose.plugins.attrib import attr

from tests.common import load_check

@attr(requires='apache')
class TestCheckApache(unittest.TestCase):
    def test_apache(self):
        agent_config = {
            'version': '0.1',
            'api_key': 'toto'
        }
        config = {
            'init_config': {},
            'instances': [
                {
                    'apache_status_url': 'http://localhost:8080/server-status',
                    'tags': ['instance:first']
                },
                {
                    'apache_status_url': 'http://localhost:8080/server-status?auto',
                    'tags': ['instance:second']
                },
            ]
        }
        check = load_check('apache', config, agent_config)

        check.check(config['instances'][0])
        metrics = check.get_metrics()
        self.assertEquals(metrics[0][3].get('tags'), ['instance:first'])

        check.check(config['instances'][1])
        metrics = check.get_metrics()
        self.assertEquals(metrics[0][3].get('tags'), ['instance:second'])

        service_checks = check.get_service_checks()
        can_connect = [sc for sc in service_checks if sc['check'] == 'apache.can_connect']
        for i in range(len(can_connect)):
            self.assertEquals(set(can_connect[i]['tags']), set(['host:localhost', 'port:8080']), service_checks)
