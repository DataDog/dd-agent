import time
import unittest
import logging
import subprocess
import shlex
import os
import signal

from nose.plugins.skip import SkipTest

from daemon import AgentSupervisor

class TestAutoRestart(unittest.TestCase):
    """ Test the auto-restart and forking of the agent """
    def setUp(self):
        self.agent_foreground = None
        self.agent_daemon = None

    def tearDown(self):
        if self.agent_foreground:
            self.agent_foreground.kill()
        if self.agent_daemon:
            args = shlex.split('python agent.py stop')
            subprocess.Popen(args).communicate()

    def _start_foreground(self):
        # Run the agent in the foreground with auto-restarting on.
        args = shlex.split('python agent.py foreground --autorestart')
        self.agent_foreground = subprocess.Popen(args)
        time.sleep(5)

    def _start_daemon(self):
        args = shlex.split('python agent.py start --autorestart')
        self.agent_daemon = subprocess.Popen(args)
        time.sleep(5)

    def _get_child_parent_pids(self, grep_str):
        args = shlex.split('pgrep -f "%s"' % grep_str)
        pgrep = subprocess.Popen(args, stdout=subprocess.PIPE,
            close_fds=True).communicate()[0]
        pids = pgrep.strip().split('\n')
        assert len(pids) == 2, pgrep

        return sorted([int(p) for p in pids], reverse=True)

    def test_foreground(self):
        self._start_foreground()

        grep_str = 'agent.py foreground'
        child_pid, parent_pid = self._get_child_parent_pids(grep_str)

        # Try killing the parent proc, confirm that the child is killed as well.
        os.kill(parent_pid, signal.SIGTERM)
        os.waitpid(parent_pid, 0)
        time.sleep(6)
        self.assertRaises(OSError, os.kill, child_pid, signal.SIGTERM)

        # Restart the foreground agent.
        self._start_foreground()
        child_pid, parent_pid = self._get_child_parent_pids(grep_str)

        # Set a SIGUSR1 to the child to force an auto-restart exit.
        os.kill(child_pid, signal.SIGUSR1)
        time.sleep(6)

        # Confirm that the child is still alive
        child_pid, parent_pid = self._get_child_parent_pids(grep_str)

        # Kill the foreground process.
        self.agent_foreground.terminate()
        self.agent_foreground = None

    def test_daemon(self):
        self._start_daemon()

        grep_str = 'agent.py start'
        child_pid, parent_pid = self._get_child_parent_pids(grep_str)

        # Try killing the parent proc, confirm that the child is killed as well.
        os.kill(parent_pid, signal.SIGTERM)
        time.sleep(6)
        self.assertRaises(OSError, os.kill, child_pid, signal.SIGTERM)

        # Restart the daemon agent.
        self._start_daemon()
        child_pid, parent_pid = self._get_child_parent_pids(grep_str)

        # Set a SIGUSR1 to the child to force an auto-restart exit.
        os.kill(child_pid, signal.SIGUSR1)
        time.sleep(6)

        # Confirm that the child is still alive
        child_pid, parent_pid = self._get_child_parent_pids(grep_str)

        # Kill the daemon process.
        os.kill(parent_pid, signal.SIGTERM)
        self.agent_daemon = None

if __name__ == '__main__':
    unittest.main()
