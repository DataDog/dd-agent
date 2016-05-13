# -*- coding: latin-1 -*-
# stdlib
import os
import os.path
import tempfile
import mock
import unittest
from shutil import copyfile, rmtree

# 3p
import ntpath

# project
from config import get_config, load_check_directory, _conf_path_to_check_name
from util import is_valid_hostname, windows_friendly_colon_split
from utils.pidfile import PidFile
from utils.platform import Platform

# No more hardcoded default checks
DEFAULT_CHECKS = []


class TestConfig(unittest.TestCase):
    CONFIG_FOLDER = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'fixtures', 'config')

    def get_config(self, name, parse_args=False):
        """
        Small helper function to load fixtures configs
        """
        return get_config(cfg_path=os.path.join(self.CONFIG_FOLDER, name), parse_args=parse_args)

    def testWhiteSpaceConfig(self):
        """Leading whitespace confuse ConfigParser
        """
        agentConfig = self.get_config('bad.conf')

        self.assertEquals(agentConfig["dd_url"], "https://app.datadoghq.com")
        self.assertEquals(agentConfig["api_key"], "1234")
        self.assertEquals(agentConfig["nagios_log"], "/var/log/nagios3/nagios.log")
        self.assertEquals(agentConfig["graphite_listen_port"], 17126)
        self.assertTrue("statsd_metric_namespace" in agentConfig)

    def test_one_endpoint(self):
        agent_config = self.get_config('one_endpoint.conf')
        self.assertEquals(agent_config["dd_url"], "https://app.datadoghq.com")
        self.assertEquals(agent_config["api_key"], "1234")
        endpoints = {'https://app.datadoghq.com': ['1234']}
        self.assertEquals(agent_config['endpoints'], endpoints)

    def test_multiple_endpoints(self):
        agent_config = self.get_config('multiple_endpoints.conf')
        self.assertEquals(agent_config["dd_url"], "https://app.datadoghq.com")
        self.assertEquals(agent_config["api_key"], "1234")
        endpoints = {
            'https://app.datadoghq.com': ['1234'],
            'https://app.example.com': ['5678', '901']
        }
        self.assertEquals(agent_config['endpoints'], endpoints)
        with self.assertRaises(AssertionError):
            self.get_config('multiple_endpoints_bad.conf')

    def test_multiple_apikeys(self):
        agent_config = self.get_config('multiple_apikeys.conf')
        self.assertEquals(agent_config["dd_url"], "https://app.datadoghq.com")
        self.assertEquals(agent_config["api_key"], "1234")
        endpoints = {
            'https://app.datadoghq.com': ['1234', '5678', '901']
        }
        self.assertEquals(agent_config['endpoints'], endpoints)

    def testGoodPidFile(self):
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
            u'234234235235235235',  # Couldn't find anything in the RFC saying it's not valid
            u'A45fsdff045-dsflk4dfsdc.ret43tjssfd',
            u'4354sfsdkfj4TEfdlv56gdgdfRET.dsf-dg',
            u'r' * 255,
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
            Platform.is_win32 = staticmethod(lambda: True)

            test_cases = [
                ("C:\\Documents\\Users\\script.py:C:\\Documents\\otherscript.py", ["C:\\Documents\\Users\\script.py", "C:\\Documents\\otherscript.py"]),
                ("C:\\Documents\\Users\\script.py:parser.py", ["C:\\Documents\\Users\\script.py", "parser.py"])
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


TMP_DIR = tempfile.gettempdir()
DD_AGENT_TEST_DIR = 'dd-agent-tests'
TEMP_3RD_PARTY_CHECKS_DIR = os.path.join(TMP_DIR, DD_AGENT_TEST_DIR, '3rd-party')
TEMP_ETC_CHECKS_DIR = os.path.join(TMP_DIR, DD_AGENT_TEST_DIR, 'etc', 'checks.d')
TEMP_ETC_CONF_DIR = os.path.join(TMP_DIR, DD_AGENT_TEST_DIR, 'etc', 'conf.d')
TEMP_AGENT_CHECK_DIR = os.path.join(TMP_DIR, DD_AGENT_TEST_DIR)
FIXTURE_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'fixtures', 'checks')


@mock.patch('config.get_checksd_path', return_value=TEMP_AGENT_CHECK_DIR)
@mock.patch('config.get_confd_path', return_value=TEMP_ETC_CONF_DIR)
@mock.patch('config.get_3rd_party_path', return_value=TEMP_3RD_PARTY_CHECKS_DIR)
class TestConfigLoadCheckDirectory(unittest.TestCase):

    TEMP_DIRS = [
        '%s/test_check' % TEMP_3RD_PARTY_CHECKS_DIR,
        TEMP_ETC_CHECKS_DIR, TEMP_ETC_CONF_DIR, TEMP_AGENT_CHECK_DIR
    ]

    def setUp(self):
        for _dir in self.TEMP_DIRS:
            if not os.path.exists(_dir):
                os.makedirs(_dir)

    def testConfigInvalid(self, *args):
        copyfile('%s/invalid_conf.yaml' % FIXTURE_PATH,
            '%s/test_check.yaml' % TEMP_ETC_CONF_DIR)
        copyfile('%s/valid_check_1.py' % FIXTURE_PATH,
            '%s/test_check.py' % TEMP_AGENT_CHECK_DIR)
        checks = load_check_directory({"additional_checksd": TEMP_ETC_CHECKS_DIR}, "foo")
        self.assertEquals(1, len(checks['init_failed_checks']))


    def test_conf_path_to_check_name(self, *args):
        """
        Resolve the check name from the full path.

        Note: Support Unix & Windows systems
        """
        # Samples
        check_name = u"haproxy"
        unix_check_path = u"/etc/dd-agent/conf.d/haproxy.yaml"
        win_check_path = u"C:\\ProgramData\\Datadog\\conf.d\\haproxy.yaml"
        with mock.patch('config.os.path.splitext', side_effect=ntpath.splitext):
            with mock.patch('config.os.path.split', side_effect=ntpath.split):
                self.assertEquals(
                    _conf_path_to_check_name(win_check_path), check_name
                )
        self.assertEquals(
            _conf_path_to_check_name(unix_check_path), check_name
        )

    def testConfigNotFound(self, *args):
        copyfile('%s/valid_conf.yaml' % FIXTURE_PATH,
            '%s/test_check.yaml' % TEMP_ETC_CONF_DIR)
        checks = load_check_directory({"additional_checksd": TEMP_ETC_CHECKS_DIR}, "foo")
        self.assertEquals(0, len(checks['init_failed_checks']))
        self.assertEquals(0, len(checks['initialized_checks']))

    def testConfigAgentOnly(self, *args):
        copyfile('%s/valid_conf.yaml' % FIXTURE_PATH,
            '%s/test_check.yaml' % TEMP_ETC_CONF_DIR)
        copyfile('%s/valid_check_1.py' % FIXTURE_PATH,
            '%s/test_check.py' % TEMP_AGENT_CHECK_DIR)
        checks = load_check_directory({"additional_checksd": TEMP_ETC_CHECKS_DIR}, "foo")
        self.assertEquals(1, len(checks['initialized_checks']))

    def testConfigETCOnly(self, *args):
        copyfile('%s/valid_conf.yaml' % FIXTURE_PATH,
            '%s/test_check.yaml' % TEMP_ETC_CONF_DIR)
        copyfile('%s/valid_check_1.py' % FIXTURE_PATH,
            '%s/test_check.py' % TEMP_ETC_CHECKS_DIR)
        checks = load_check_directory({"additional_checksd": TEMP_ETC_CHECKS_DIR}, "foo")
        self.assertEquals(1, len(checks['initialized_checks']))

    def testConfigAgentETC(self, *args):
        copyfile('%s/valid_conf.yaml' % FIXTURE_PATH,
            '%s/test_check.yaml' % TEMP_ETC_CONF_DIR)
        copyfile('%s/valid_check_2.py' % FIXTURE_PATH,
            '%s/test_check.py' % TEMP_AGENT_CHECK_DIR)
        copyfile('%s/valid_check_1.py' % FIXTURE_PATH,
            '%s/test_check.py' % TEMP_ETC_CHECKS_DIR)
        checks = load_check_directory({"additional_checksd": TEMP_ETC_CHECKS_DIR}, "foo")
        self.assertEquals(1, len(checks['initialized_checks']))
        self.assertEquals('valid_check_1', checks['initialized_checks'][0].check(None))

    def testConfigCheckNotAgentCheck(self, *args):
        copyfile('%s/valid_conf.yaml' % FIXTURE_PATH,
            '%s/test_check.yaml' % TEMP_ETC_CONF_DIR)
        copyfile('%s/invalid_check_1.py' % FIXTURE_PATH,
            '%s/test_check.py' % TEMP_AGENT_CHECK_DIR)
        checks = load_check_directory({"additional_checksd": TEMP_ETC_CHECKS_DIR}, "foo")
        self.assertEquals(0, len(checks['init_failed_checks']))
        self.assertEquals(0, len(checks['initialized_checks']))

    def testConfigCheckImportError(self, *args):
        copyfile('%s/valid_conf.yaml' % FIXTURE_PATH,
            '%s/test_check.yaml' % TEMP_ETC_CONF_DIR)
        copyfile('%s/invalid_check_2.py' % FIXTURE_PATH,
            '%s/test_check.py' % TEMP_AGENT_CHECK_DIR)
        checks = load_check_directory({"additional_checksd": TEMP_ETC_CHECKS_DIR}, "foo")
        self.assertEquals(1, len(checks['init_failed_checks']))

    def testConfig3rdPartyAgent(self, *args):
        copyfile('%s/valid_conf.yaml' % FIXTURE_PATH,
            '%s/test_check.yaml' % TEMP_ETC_CONF_DIR)
        copyfile('%s/valid_check_2.py' % FIXTURE_PATH,
            '%s/test_check.py' % TEMP_AGENT_CHECK_DIR)
        copyfile('%s/valid_check_1.py' % FIXTURE_PATH,
            '%s/test_check/check.py' % TEMP_3RD_PARTY_CHECKS_DIR)
        checks = load_check_directory({"additional_checksd": TEMP_ETC_CHECKS_DIR}, "foo")
        self.assertEquals(1, len(checks['initialized_checks']))
        self.assertEquals('valid_check_1', checks['initialized_checks'][0].check(None))

    def testConfigETC3rdParty(self, *args):
        copyfile('%s/valid_conf.yaml' % FIXTURE_PATH,
            '%s/test_check.yaml' % TEMP_ETC_CONF_DIR)
        copyfile('%s/valid_check_2.py' % FIXTURE_PATH,
            '%s/test_check/check.py' % TEMP_3RD_PARTY_CHECKS_DIR)
        copyfile('%s/valid_check_1.py' % FIXTURE_PATH,
            '%s/test_check.py' % TEMP_ETC_CHECKS_DIR)
        checks = load_check_directory({"additional_checksd": TEMP_ETC_CHECKS_DIR}, "foo")
        self.assertEquals(1, len(checks['initialized_checks']))
        self.assertEquals('valid_check_1', checks['initialized_checks'][0].check(None))

    def testConfigInheritedCheck(self, *args):
        copyfile('%s/valid_conf.yaml' % FIXTURE_PATH,
            '%s/test_check.yaml' % TEMP_ETC_CONF_DIR)
        copyfile('%s/valid_sub_check.py' % FIXTURE_PATH,
            '%s/test_check.py' % TEMP_ETC_CHECKS_DIR)
        checks = load_check_directory({"additional_checksd": TEMP_ETC_CHECKS_DIR}, "foo")
        self.assertEquals(1, len(checks['initialized_checks']))
        self.assertEquals('valid_check_1', checks['initialized_checks'][0].check(None))

    def testConfigDeprecatedNagiosConfig(self, *args):
        copyfile('%s/valid_check_1.py' % FIXTURE_PATH,
            '%s/nagios.py' % TEMP_ETC_CHECKS_DIR)
        checks = load_check_directory({"nagios_perf_cfg": None, "additional_checksd": TEMP_ETC_CHECKS_DIR}, "foo")
        self.assertEquals(1, len(checks['initialized_checks']))
        self.assertEquals('valid_check_1', checks['initialized_checks'][0].check(None))

    def testConfigDefault(self, *args):
        copyfile('%s/valid_conf.yaml' % FIXTURE_PATH,
            '%s/test_check.yaml.default' % TEMP_ETC_CONF_DIR)
        copyfile('%s/valid_check_1.py' % FIXTURE_PATH,
            '%s/test_check.py' % TEMP_ETC_CHECKS_DIR)
        checks = load_check_directory({"additional_checksd": TEMP_ETC_CHECKS_DIR}, "foo")
        self.assertEquals(1, len(checks['initialized_checks']))

    def testConfigCustomOverDefault(self, *args):
        copyfile('%s/valid_conf.yaml' % FIXTURE_PATH,
            '%s/test_check.yaml.default' % TEMP_ETC_CONF_DIR)
        # a 2nd valid conf file, slightly different so that we can test which one has been picked up
        # (with 2 instances for instance)
        copyfile('%s/valid_conf_2.yaml' % FIXTURE_PATH,
            '%s/test_check.yaml' % TEMP_ETC_CONF_DIR)
        copyfile('%s/valid_check_1.py' % FIXTURE_PATH,
            '%s/test_check.py' % TEMP_ETC_CHECKS_DIR)
        checks = load_check_directory({"additional_checksd": TEMP_ETC_CHECKS_DIR}, "foo")
        self.assertEquals(1, len(checks['initialized_checks']))
        self.assertEquals(2, checks['initialized_checks'][0].instance_count())  # check that we picked the right conf

    def tearDown(self):
        for _dir in self.TEMP_DIRS:
            rmtree(_dir)
