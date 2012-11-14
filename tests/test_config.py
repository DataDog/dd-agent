import unittest
import os.path
import tempfile

from config import get_config

from util import PidFile

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

if __name__ == '__main__':
    unittest.main()

