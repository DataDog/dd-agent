# stdlib
import time
import socket
# 3p
import paramiko
# project
from checks import AgentCheck

class CheckSSH(AgentCheck):

    def _load_conf(self, instance):
        if 'host' not in instance or not instance['host']:
            raise Exception ("No host has been specified")  #maybe use dict instead
        else:
            host = instance['host']

        if 'port' not in instance:
            self.log.info("No port specified, defaulted to 22")
            port = 22
        else:
            port = int(instance['port'])

        if 'username' not in instance or not instance['username']:
            raise Exception ("No username has been specified")
        else:
            username = instance['username']

        if 'password' not in instance or not instance['password']:
            self.log.info("No password specified")
            password = None
        else:
            password = instance['password']

        if 'private_key' not in instance or not instance['private_key']:
            self.log.info("No private_key specified")
            private_key = None
        else:
            private_key = instance['private_key']

        return host, port, username, password, private_key

    def check(self, instance):
        host, port, username, password, private_key = self._load_conf(instance)

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.load_system_host_keys()

        try:
            exception_message = 'No errors'
            client.connect(host, port=port, username=username, password=password, pkey=private_key)

        except Exception as e:
            exception_message = "{0}".format(e)

        #Service Availability to see if up or down
        if exception_message == 'No errors':
            try:
                sftp = client.open_sftp()
            except Exception as e:
                exception_message = "{0}".format(e)
                status = AgentCheck.CRITICAL

            start_time = time.time()

            try:
                result = sftp.listdir('.')
            except Exception as e:
                exception_message = "{0}".format(e)
                status = AgentCheck.CRITICAL

            if result is not None:
                status = AgentCheck.OK
                end_time = time.time()
                time_taken = end_time - start_time
                self.gauge('ssh.response_time', time_taken)
            else:
                status = AgentCheck.CRITICAL
                exception_message = 'An error has occured'
        else:
            status = AgentCheck.CRITICAL

        self.service_check('sftp.can_connect', status, message=exception_message)
