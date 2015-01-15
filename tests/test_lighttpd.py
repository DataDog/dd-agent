import unittest
from nose.plugins.attrib import attr
from tests.common import load_check

@attr(requires='lighttpd')
class TestLighttpd(unittest.TestCase):

    def setUp(self):
        self.agent_config = {
            'version': '0.1',
            'api_key': 'toto'
        }
        self.config = {
            'instances': [
                {
                    'lighttpd_status_url': 'http://localhost:9449/server-status',
                    'tags': ['instance:first'],
                },
                {
                    'lighttpd_status_url': 'http://localhost:9449/server-status?auto',
                    'tags': ['instance:second'],
                },
            ]
        }


    def test_lighttpd(self):
        l = load_check('lighttpd', self.config, self.agent_config)

        l.check(self.config['instances'][0])
        metrics = l.get_metrics()
        self.assertEquals(metrics[0][3].get('tags'), ['instance:first'])

        l.check(self.config['instances'][1])
        metrics = l.get_metrics()
        self.assertEquals(metrics[0][3].get('tags'), ['instance:second'])
        service_checks = l.get_service_checks()
        can_connect = [sc for sc in service_checks if sc['check'] == 'lighttpd.can_connect']
        for i in range(len(can_connect)):
            self.assertEquals(set(can_connect[i]['tags']), set(['host:localhost', 'port:9449']), service_checks)


if __name__ == '__main__':
    unittest.main()
