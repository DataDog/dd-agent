# stdlib
import subprocess  # noqa

# third party
import mock

# project
from tests.checks.common import AgentCheckTest


class Fail2BanTestCase(AgentCheckTest):
    CHECK_NAME = 'fail2ban'

    def setUp(self):
        self.config = {
            "instances": [
                {
                    "sudo": True,
                },
            ],
        }
        self.load_check(self.config)

    def test_execute_command(self):
        with mock.patch("subprocess.Popen") as popen:
            popen.return_value = mock.Mock()
            popen.return_value.returncode = 0
            popen.return_value.communicate.return_value = ("Output\nHere", None)
            output = self.check.execute_command(["some", "args"])
            self.assertEquals(["Output", "Here"], list(output))
            args = list(popen.call_args)
            self.assertTrue(["some", "args"] in args[0])

    def test_execute_command_sudo(self):
        with mock.patch("subprocess.Popen") as popen:
            popen.return_value = mock.Mock()
            popen.return_value.returncode = 0
            popen.return_value.communicate.return_value = ("Output\nHere", None)
            output = self.check.execute_command(["some", "args"], sudo=True)
            self.assertEquals(["Output", "Here"], list(output))
            args = list(popen.call_args)
            self.assertTrue(["sudo", "some", "args"] in args[0])

    def test_get_jails(self):
        with mock.patch.object(self.check, "execute_command") as execute_command:
            execute_command.return_value = [
                "Status",
                "|- Number of jail:\t2"
                "`- Jail list:\tssh, ssh-ddos"
            ]

            self.assertEquals(["ssh", "ssh-ddos"], list(self.check.get_jails()))
            self.assertEquals(["ssh"], list(self.check.get_jails(jail_blacklist=["ssh-ddos"])))
            self.assertEquals([], list(self.check.get_jails(jail_blacklist=["ssh-ddos", "ssh"])))

    def test_get_jail_status(self):
        status_output = [
            "Status for the jail: ssh",
            "|- filter",
            "|  |- File list:\t/var/log/auth.log",
            "|  |- Currently failed:\t2",
            "|  `- Total failed:\t62219",
            "`- action",
            "   |- Currently banned:\t2",
            "   |  `- IP list:\t104.217.154.54 222.186.56.43",
            "   `- Total banned:\t4985"
        ]
        expected = {
            "filter": {
                "file_list": "/var/log/auth.log",
                "currently_failed": "2",
                "total_failed": "62219"
            },
            "action": {
                "currently_banned": "2",
                "ip_list": "104.217.154.54 222.186.56.43",
                "total_banned": "4985"
            }
        }
        with mock.patch.object(self.check, "execute_command") as execute_command:
            execute_command.return_value = status_output
            status = self.check.get_jail_status("ssh")
            self.assertEqual(expected, status)

    def test_get_jail_stats(self):
        jails = ["ssh"]
        jail_status = {
            "filter": {
                "file_list": "/var/log/auth.log",
                "currently_failed": "2",
                "total_failed": "62219"
            },
            "action": {
                "currently_banned": "2",
                "ip_list": "104.217.154.54 222.186.56.43",
                "total_banned": "4985"
            }
        }
        expected = [
            ("ssh", "fail2ban.action.currently_banned", "2"),
            ("ssh", "fail2ban.action.total_banned", "4985"),
            ("ssh", "fail2ban.filter.currently_failed", "2"),
            ("ssh", "fail2ban.filter.total_failed", "62219")
        ]
        with mock.patch.object(self.check, "get_jail_status") as get_jail_status:
            with mock.patch.object(self.check, "get_jails") as get_jails:
                get_jails.return_value = jails
                get_jail_status.return_value = jail_status
                stats = self.check.get_jail_stats()
                self.assertEquals(expected, list(stats))

    def test_can_ping_fail2ban_pong(self):
        with mock.patch.object(self.check, "execute_command") as execute_command:
            execute_command.return_value = ["Server replied: pong"]
            self.assertTrue(self.check.can_ping_fail2ban())
            execute_command.assert_called_with(["fail2ban-client", "ping"], sudo=False)

    def test_can_ping_fail2ban_fail(self):
        with mock.patch.object(self.check, "execute_command") as execute_command:
            # if it cannot connect we will get a subprocess.CalledProcessError
            # which means execute_command will return []
            execute_command.return_value = []
            self.assertFalse(self.check.can_ping_fail2ban())
            execute_command.assert_called_with(["fail2ban-client", "ping"], sudo=False)

    def test_check(self):
        def mock_can_ping_fail2ban(sudo=False):
            return True

        def mock_get_jail_stats(sudo=False, jail_blacklist=None):
            return [
                ("ssh", "fail2ban.action.currently_banned", "2"),
                ("ssh", "fail2ban.action.total_banned", "4985"),
                ("ssh", "fail2ban.filter.currently_failed", "2"),
                ("ssh", "fail2ban.filter.total_failed", "62219")
            ]

        mocks = {
            "can_ping_fail2ban": mock_can_ping_fail2ban,
            "get_jail_stats": mock_get_jail_stats,
        }

        self.run_check(self.config, mocks=mocks)
        expected_metrics = [
            ('fail2ban.filter.total_failed', '62219', ['jail:ssh']),
            ('fail2ban.action.total_banned', '4985', ['jail:ssh']),
            ('fail2ban.action.currently_banned', '2', ['jail:ssh']),
            ('fail2ban.filter.currently_failed', '2', ['jail:ssh'])
        ]
        for metric, value, tags in expected_metrics:
            self.assertMetric(metric, value=value, tags=tags)
