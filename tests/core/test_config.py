# -*- coding: latin-1 -*-
# stdlib
import os
import os.path
import tempfile
import unittest

# project
from config import get_config, load_check_directory
from util import is_valid_hostname, windows_friendly_colon_split
from utils.pidfile import PidFile
from utils.platform import Platform

# No more hardcoded default checks
DEFAULT_CHECKS = []

class TestConfig(unittest.TestCase):
    def testWhiteSpaceConfig(self):
        """Leading whitespace confuse ConfigParser
        """
        agentConfig = get_config(cfg_path=os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                                       'fixtures', 'badconfig.conf'),
                                 parse_args=False)
        self.assertEquals(agentConfig["dd_url"], "https://app.datadoghq.com")
        self.assertEquals(agentConfig["api_key"], "1234")
        self.assertEquals(agentConfig["nagios_log"], "/var/log/nagios3/nagios.log")
        self.assertEquals(agentConfig["graphite_listen_port"], 17126)
        self.assertTrue("statsd_metric_namespace" in agentConfig)

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
        self.assertEquals(path, os.path.join(tempfile.gettempdir(), 'test.pid'))

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

    def testWindowsSplit(self):
        # Make the function run as if it was on windows
        func = Platform.is_win32
        try:
            Platform.is_win32 = staticmethod(lambda : True)

            test_cases = [
                ("C:\\Documents\\Users\\script.py:C:\\Documents\\otherscript.py", ["C:\\Documents\\Users\\script.py","C:\\Documents\\otherscript.py"]),
                ("C:\\Documents\\Users\\script.py:parser.py", ["C:\\Documents\\Users\\script.py","parser.py"])
            ]

            for test_case, expected_result in test_cases:
                self.assertEqual(windows_friendly_colon_split(test_case), expected_result)
        finally:
            # cleanup
            Platform.is_win32 = staticmethod(func)

    def testDefaultChecks(self):
        checks = load_check_directory({"additional_checksd": "/etc/dd-agent/checks.d/"}, "foo")
        init_checks_names = [c.name for c in checks['initialized_checks']]

        for c in DEFAULT_CHECKS:
            self.assertTrue(c in init_checks_names)
