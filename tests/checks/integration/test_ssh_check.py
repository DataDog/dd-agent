# stdlib
import unittest

# 3p
from nose.plugins.attrib import attr

# project
from checks import AgentCheck
from tests.checks.common import load_check


@attr(requires='ssh')
class SshTestCase(unittest.TestCase):

    def test_ssh(self):
        config = {
            'instances': [{
                'host': 'io.netgarage.org',
                'port': 22,
                'username': 'level1',
                'password': 'level1',
                'sftp_check': False,
                'private_key_file': '',
                'add_missing_keys': True
            }, {
                'host': 'localhost',
                'port': 22,
                'username': 'test',
                'password': 'yodawg',
                'sftp_check': False,
                'private_key_file': '',
                'add_missing_keys': True
            }, {
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

        # Testing that connection will work
        self.check.check(config['instances'][0])

        service = self.check.get_service_checks()
        self.assertEqual(service[0].get('status'), AgentCheck.OK)
        self.assertEqual(service[0].get('message'), None)
        self.assertEqual(service[0].get('tags'), ["instance:io.netgarage.org-22"])

        # Testing that bad authentication will raise exception
        self.assertRaises(Exception, self.check.check, config['instances'][1])
        # Testing that bad hostname will raise exception
        self.assertRaises(Exception, self.check.check, config['instances'][2])
        service_fail = self.check.get_service_checks()
        # Check failure status
        self.assertEqual(service_fail[0].get('status'), AgentCheck.CRITICAL)
