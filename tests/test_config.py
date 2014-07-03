## -*- coding: latin-1 -*-
import unittest
import os.path
import tempfile

from config import get_config

from util import PidFile, is_valid_hostname

class TestConfig(unittest.TestCase):
    def testWhiteSpaceConfig(self):
        """Leading whitespace confuse ConfigParser
        """
        agentConfig = get_config(cfg_path=os.path.join(os.path.dirname(os.path.realpath(__file__)), "badconfig.conf"))
        self.assertEquals(agentConfig["dd_url"], "https://app.datadoghq.com")
        self.assertEquals(agentConfig["api_key"], "1234")
        self.assertEquals(agentConfig["nagios_log"], "/var/log/nagios3/nagios.log")
        self.assertEquals(agentConfig["graphite_listen_port"], 17126)

    def testGoodPidFie(self):
        """Verify that the pid file succeeds and fails appropriately"""

        pid_dir = tempfile.mkdtemp()
        program = 'test'

        expected_path = os.path.join(pid_dir, '%s.pid' % program)
        pid = "666"
        pid_f = open(expected_path, 'w')
        pid_f.write(pid)
        pid_f.close()

        p = PidFile(program, pid_dir)

        self.assertEquals(p.get_pid(), 666)
        # clean up
        self.assertEquals(p.clean(), True)
        self.assertEquals(os.path.exists(expected_path), False)

    def testBadPidFile(self):
        pid_dir = "/does-not-exist"

        p = PidFile('test', pid_dir)
        path = p.get_path()
        self.assertEquals(path, "/tmp/test.pid")

        pid = "666"
        pid_f = open(path, 'w')
        pid_f.write(pid)
        pid_f.close()

        self.assertEquals(p.get_pid(), 666)
        self.assertEquals(p.clean(), True)
        self.assertEquals(os.path.exists(path), False)

    def testHostname(self):
        valid_hostnames = [
            u'i-123445',
            u'5dfsdfsdrrfsv',
            u'432498234234A'
            u'234234235235235235', # Couldn't find anything in the RFC saying it's not valid
            u'A45fsdff045-dsflk4dfsdc.ret43tjssfd',
            u'4354sfsdkfj4TEfdlv56gdgdfRET.dsf-dg',
            u'r'*255,
        ]

        not_valid_hostnames = [
            u'abc' * 150,
            u'sdf4..sfsd',
            u'$42sdf',
            u'.sfdsfds'
            u's™£™£¢ª•ªdfésdfs'
        ]

        for hostname in valid_hostnames:
            self.assertTrue(is_valid_hostname(hostname), hostname)

        for hostname in not_valid_hostnames:
            self.assertFalse(is_valid_hostname(hostname), hostname)

if __name__ == '__main__':
    unittest.main()

