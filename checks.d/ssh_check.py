# stdlib
import time
import socket
# 3p
import paramiko
from collections import namedtuple
# project
from checks import AgentCheck

class CheckSSH(AgentCheck):

    OPTIONS = [
        ('host', True, None, str),
        ('port', False, 22, int),
        ('username', True, None, str),
        ('password', False, None, str),
        ('private_key_file', False, None, str),
        ('sftp_check', False, True, bool),
        ('add_missing_keys', False, False, bool),
    ]

    Config = namedtuple('Config', [
                'host',
                'port',
                'username',
                'password',
                'private_key_file',
                'sftp_check',
                'add_missing_keys',
            ]
            )
    def _load_conf(self, instance):
        params = []
        for option, required, default, expected_type in self.OPTIONS:
            value = instance.get(option)
            if required and (not value or type(value)) != expected_type :
                raise Exception("Please specify a valid {0}".format(option))

            if value is None or type(value) != expected_type:
                self.log.debug("Bad or missing value for {0} parameter. Using default".format(option))
                value = default

            params.append(value)
        return self.Config._make(params)

    def check(self, instance):
        host, port, username, password, private_key_file, sftp_check, add_missing_keys = self._load_conf(instance)

        try:
            private_key = paramiko.RSAKey.from_private_key_file (private_key_file)
        except Exception:
            self.log.debug("Private Key not found")
            private_key = None

        client = paramiko.SSHClient()
        if add_missing_keys:
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.load_system_host_keys()

        exception_message = None
        #Service Availability to check status of SSH
        try:
            client.connect(host, port=port, username=username, password=password, pkey=private_key)
            self.service_check('ssh.can_connect', AgentCheck.OK, message=exception_message)

        except Exception as e:
            exception_message = str(e)
            self.service_check('ssh.can_connect', AgentCheck.CRITICAL, message=exception_message)

        #Service Availability to check status of SFTP
        if sftp_check:
            if exception_message is None:
                try:
                    sftp = client.open_sftp()
                    #Check response time of SFTP
                    start_time = time.time()

                    result = sftp.listdir('.')
                    status = AgentCheck.OK
                    end_time = time.time()
                    time_taken = end_time - start_time
                    self.gauge('sftp.response_time', time_taken)

                except Exception as e:
                    exception_message = str(e)
                    status = AgentCheck.CRITICAL

            else:
                status = AgentCheck.CRITICAL
                exception_message = "Failed because of SSH: " + exception_message

            if exception_message is None:
                exception_message = "No errors occured"

            self.service_check('sftp.can_connect', status, message=exception_message)
