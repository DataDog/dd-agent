import unittest
import os.path
from config import *

class TestConfig(unittest.TestCase):
    def testWhiteSpaceConfig(self):
        """Leading whitespace confuse ConfigParser
        """
        agentConfig, rawConfig = get_config(cfg_path=os.path.join(os.path.dirname(os.path.realpath(__file__)), "badconfig.conf"))
        self.assertEquals(agentConfig["ddUrl"], "https://app.datadoghq.com")
        self.assertEquals(agentConfig["apiKey"], "1234")
        self.assertEquals(agentConfig["nagios_log"], "/var/log/nagios3/nagios.log")
        self.assertEquals(agentConfig["graphite_listen_port"], 17126)
