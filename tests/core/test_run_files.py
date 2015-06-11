# stdlib
import os
import shlex
import signal
import subprocess
import time
import unittest

# 3p
import mock
from nose.plugins.attrib import attr

# Mock gettempdir for testing
import tempfile; tempfile.gettempdir = mock.Mock(return_value='/a/test/tmp/dir')

# project
# Mock _windows_commondata_path for testing
import config; config._windows_commondata_path = mock.Mock(return_value='./windows_commondata')


from utils.pidfile import PidFile
from checks.check_status import AgentStatus

class TestRunFiles(unittest.TestCase):
    """ Tests that runfiles (.pid, .sock, .pickle etc.) are written to internal agent folders"""

    # Mac run directory expected location
    _my_dir = os.path.dirname(os.path.abspath(__file__))
    _mac_run_dir = '/'.join(_my_dir.split('/')[:-4])

    def setUp(self):
        self.agent_daemon = None

    def tearDown(self):
        if self.agent_daemon:
            args = shlex.split('python agent.py stop')
            subprocess.Popen(args).communicate()

    @mock.patch('utils.platform.Platform.is_win32', return_value=True)
    def test_agent_status_pickle_file_win32(self, *mocks):
        ''' Test pickle file location on win32 '''
        expected_path = os.path.join('.', 'windows_commondata', 'Datadog', 'AgentStatus.pickle')
        # check AgentStatus pickle created
        self.assertEqual(AgentStatus._get_pickle_path(), expected_path)

    @mock.patch('utils.pidfile.PidFile.get_dir', return_value=_mac_run_dir)
    @mock.patch('utils.platform.Platform.is_win32', return_value=False)
    @mock.patch('utils.platform.Platform.is_mac', return_value=True)
    def test_agent_status_pickle_file_mac_dmg(self, *mocks):
        ''' Test pickle file location when running a Mac DMG install '''
        expected_path = os.path.join(self._mac_run_dir, 'AgentStatus.pickle')
        self.assertEqual(AgentStatus._get_pickle_path(), expected_path)

    @mock.patch('utils.platform.Platform.is_win32', return_value=False)
    @mock.patch('utils.platform.Platform.is_mac', return_value=True)
    def test_agent_status_pickle_file_mac_source(self, *mocks):
        ''' Test pickle file location when running a Mac source install '''
        expected_path = os.path.join('/a/test/tmp/dir', 'AgentStatus.pickle')
        self.assertEqual(AgentStatus._get_pickle_path(), expected_path)
