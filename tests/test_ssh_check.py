import unittest
from tests.common import load_check
from checks import AgentCheck

class SshTestCase(unittest.TestCase):

    def test_ssh(self):

        config = {
            'instances': [{
                'host': 'sdf.org',
                'port': 22,
                'username': 'datadog01',
                'password': 'abcd',
                'sftp_check': False,
                'private_key_file': '',
                'add_missing_keys': True
            },
            {
                'host': 'sdf.org',
                'port': 22,
                'username': 'wrongusername',
                'password': 'wrongpassword',
                'sftp_check': False,
                'private_key_file': '',
                'add_missing_keys': True
            },
            {
                'host': 'wronghost',
                'port': 22,
                'username': 'datadog01',
                'password': 'abcd',
                'sftp_check': False,
                'private_key_file': '',
                'add_missing_keys': True
            },
            ]
        }

        agentConfig = {}
        self.check = load_check('ssh_check', config, agentConfig)

        #Testing that connection will work
        self.check.check(config['instances'][0])

        service = self.check.get_service_checks()
        self.assertEqual(service[0].get('status'), AgentCheck.OK)
        self.assertEqual(service[0].get('message'), None)

        #Testing that bad authentication will raise exception
        self.assertRaises(Exception, self.check.check, config['instances'][1])
        #Testing that bad hostname will raise exception
        self.assertRaises(Exception, self.check.check, config['instances'][2])
        service_fail = self.check.get_service_checks()
        self.assertEqual(service_fail[0].get('status'), AgentCheck.CRITICAL)
