import unittest
import logging
from nose.plugins.attrib import attr
logger = logging.getLogger(__file__)

from tests.common import load_check

@attr(requires='fluentd')
class TestFluentd(unittest.TestCase):

    def test_fluentd(self):
        config = {
            "init_config": {
            },
            "instances": [
                {
                    "monitor_agent_url": "http://localhost:24220/api/plugins.json",
                    "plugin_ids": [ "plg1" ],
                }
            ]
        }

        agentConfig = {
            'version': '0.1',
            'api_key': 'toto'
        }

        check = load_check('fluentd', config, agentConfig)
        check.run()
        metrics = check.get_metrics()
        for m in metrics:
            if m[0] == 'fluentd.forward.retry_count':
                self.assertEquals(m[2], 0)
            elif m[0] == 'fluentd.forward.buffer_queue_length':
                self.assertEquals(m[2], 0)
            elif m[0] == 'fluentd.forward.buffer_total_queued_size':
                self.assertEquals(m[2], 0)
            self.assertEquals(m[3]['type'], 'gauge')
            self.assertEquals(m[3]['tags'], ['plugin_id:plg1'])

        self.assertEquals(len(metrics), 3, metrics)

        service_checks = check.get_service_checks()
        service_checks_count = len(service_checks)
        self.assertTrue(type(service_checks) == type([]))
        self.assertTrue(service_checks_count > 0)

        is_ok = [sc for sc in service_checks if sc['check'] == check.SERVICE_CHECK_NAME]
        self.assertEquals(len(is_ok), 1, service_checks)
        self.assertEquals(set(is_ok[0]['tags']), set(['fluentd_host:localhost', 'fluentd_port:24220']), service_checks)

    def test_fluentd_exception(self):
        config = {
            "init_config": {
            },
            "instances": [
                {
                    "monitor_agent_url": "http://localhost:24222/api/plugins.json",
                    "plugin_ids": [ "plg2" ],
                }
            ]
        }

        agentConfig = {
            'version': '0.1',
            'api_key': 'toto'
        }

        check = load_check('fluentd', config, agentConfig)
        self.assertRaises(Exception, check.run())

if __name__ == '__main__':
    unittest.main()
