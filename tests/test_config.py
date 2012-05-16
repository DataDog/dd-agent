import unittest
import os.path
import tempfile

from config import get_config
from agent import getPidFile, cleanPidFile, getPid

class TestConfig(unittest.TestCase):
    def testWhiteSpaceConfig(self):
        """Leading whitespace confuse ConfigParser
        """
        agentConfig = get_config(cfg_path=os.path.join(os.path.dirname(os.path.realpath(__file__)), "badconfig.conf"))
        self.assertEquals(agentConfig["ddUrl"], "https://app.datadoghq.com")
        self.assertEquals(agentConfig["apiKey"], "1234")
        self.assertEquals(agentConfig["nagios_log"], "/var/log/nagios3/nagios.log")
        self.assertEquals(agentConfig["graphite_listen_port"], 17126)

    def testGoodPidFie(self):
        """Verify that the pid file succeeds and fails appropriately"""
        # Pidfile always writable
        pid_dir = tempfile.mkdtemp()
        pid_file = getPidFile(pid_dir)
        pid = "666"
        pid_f = open(pid_file, 'w')
        pid_f.write(pid)
        pid_f.close()
        self.assertEquals(getPid(pid_dir), 666)
        # clean up
        self.assertEquals(cleanPidFile(pid_dir), True)
        self.assertEquals(os.path.exists(pid_file), False)

    def testBadPidFile(self):
        pid_dir = "/does-not-exist"
        pid_file = getPidFile(pid_dir)
        self.assertEquals(pid_file, "/tmp/dd-agent.pid")
        pid = "666"
        pid_f = open(pid_file, 'w')
        pid_f.write(pid)
        pid_f.close()
        self.assertEquals(getPid(pid_dir), 666)
        self.assertEquals(cleanPidFile(pid_dir), True)
        self.assertEquals(os.path.exists(pid_file), False)

if __name__ == '__main__':
    unittest.main()

