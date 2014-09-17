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
            raise Exception ("No host has been specified")
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

        if 'sftp_check' not in instance or instance['sftp_check'] == None:
            self.log.info("Default: sftp check true")
            sftp_check = True
        elif type(instance['sftp_check']) == str:
            self.log.info("Default: sftp check true")
            sftp_check = True
        else:
            sftp_check = instance['sftp_check']

        return host, port, username, password, private_key, sftp_check

    def check(self, instance):
        host, port, username, password, private_key, sftp_check = self._load_conf(instance)

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.load_system_host_keys()

        exception_message = None
        #Service Availability to check status of SSH
        try:
            client.connect(host, port=port, username=username, password=password, pkey=private_key)
            self.service_check('ssh.can_connect', AgentCheck.OK, message=exception_message)

        except Exception as e:
            exception_message = "{0}".format(e)
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
                    exception_message = "{0}".format(e)
                    status = AgentCheck.CRITICAL

            else:
                status = AgentCheck.CRITICAL
                exception_message = "Failed because of SSH: " + exception_message

            if exception_message is None:
                exception_message = "No errors occured"

            self.service_check('sftp.can_connect', status, message=exception_message)
