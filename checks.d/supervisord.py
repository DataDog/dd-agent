from collections import defaultdict
import errno
import socket
import time
import xmlrpclib

from checks import AgentCheck

import supervisor.xmlrpc

DEFAULT_HOST = 'localhost'
DEFAULT_PORT = '9001'
DEFAULT_SOCKET_IP = 'http://127.0.0.1'

DD_STATUS = {
    'STOPPED': AgentCheck.CRITICAL,
    'STARTING': AgentCheck.UNKNOWN,
    'RUNNING': AgentCheck.OK,
    'BACKOFF': AgentCheck.CRITICAL,
    'STOPPING': AgentCheck.CRITICAL,
    'EXITED': AgentCheck.CRITICAL,
    'FATAL': AgentCheck.CRITICAL,
    'UNKNOWN': AgentCheck.UNKNOWN
}

PROCESS_STATUS = {
    AgentCheck.CRITICAL: 'down',
    AgentCheck.OK: 'up',
    AgentCheck.UNKNOWN: 'unknown'
}

SERVER_TAG = 'supervisord_server'

PROCESS_TAG = 'supervisord_process'

FORMAT_TIME = lambda x: time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(x))

SERVER_SERVICE_CHECK = 'supervisord.can_connect'
PROCESS_SERVICE_CHECK = 'supervisord.process.status'

class SupervisordCheck(AgentCheck):

    def check(self, instance):
        server_name = instance.get('name')

        if not server_name or not server_name.strip():
            raise Exception("Supervisor server name not specified in yaml configuration.")

        server_service_check_tags = ['%s:%s' % (SERVER_TAG, server_name)]
        supe = self._connect(instance)
        count_by_status = defaultdict(int)

        # Grab process information
        try:
            proc_names = instance.get('proc_names')
            if proc_names:
                if not isinstance(proc_names, list) or not len(proc_names):
                    raise Exception("Empty or invalid proc_names.")
                processes = []
                for proc_name in proc_names:
                    try:
                        processes.append(supe.getProcessInfo(proc_name))
                    except xmlrpclib.Fault, e:
                        if e.faultCode == 10: # bad process name
                            self.warning('Process not found: %s' % proc_name)
                        else:
                            raise Exception('An error occurred while reading'
                                            'process %s information: %s %s'
                                            % (proc_name, e.faultCode, e.faultString))
            else:
                processes = supe.getAllProcessInfo()
        except socket.error, e:
            host = instance.get('host', DEFAULT_HOST)
            port = instance.get('port', DEFAULT_PORT)
            sock = instance.get('socket')
            if sock is None:
                msg = 'Cannot connect to http://%s:%s. ' \
                    'Make sure that supervisor is running and XML-RPC ' \
                    'inet interface is enabled.' % (host, port)
            else:
                msg = 'Cannot connect to %s. Make sure that supervisor ' \
                    'is running and that the socket file' \
                    ' has the right permissions.' % sock

            self.service_check(SERVER_SERVICE_CHECK, AgentCheck.CRITICAL,
                               tags=server_service_check_tags,
                               message=msg)

            raise Exception(msg)
        except xmlrpclib.ProtocolError, e:
            if e.errcode == 401: # authorization error
                msg = 'Username or password to %s are incorrect.' % server_name
            else:
                msg = "An error occurred while connecting to %s: "\
                    "%s %s " % (server_name, e.errcode, e.errmsg)

            self.service_check(SERVER_SERVICE_CHECK, AgentCheck.CRITICAL,
                               tags=server_service_check_tags,
                               message=msg)
            raise Exception(msg)


        # If we're here, we were able to connect to the server
        self.service_check(SERVER_SERVICE_CHECK, AgentCheck.OK,
            tags=server_service_check_tags)

        # Report service checks and uptime for each process
        for proc in processes:
            proc_name = proc['name']
            tags = ['%s:%s' % (SERVER_TAG, server_name),
                    '%s:%s' % (PROCESS_TAG, proc_name)]

            # Report Service Check
            status = DD_STATUS[proc['statename']]
            msg = self._build_message(proc)
            count_by_status[status] += 1
            self.service_check(PROCESS_SERVICE_CHECK,
                               status, tags=tags, message=msg)
            # Report Uptime
            uptime = self._extract_uptime(proc)
            self.gauge('supervisord.process.uptime', uptime, tags=tags)

        # Report counts by status
        tags = ['%s:%s' % (SERVER_TAG, server_name)]
        for status in PROCESS_STATUS:
            self.gauge('supervisord.process.count', count_by_status[status],
                       tags=tags + ['status:%s' % PROCESS_STATUS[status]])

    @staticmethod
    def _connect(instance):
        sock = instance.get('socket')
        if sock is not None:
            host = instance.get('host', DEFAULT_SOCKET_IP)
            transport = supervisor.xmlrpc.SupervisorTransport(None, None, sock)
            server = xmlrpclib.ServerProxy(host, transport=transport)
        else:
            host = instance.get('host', DEFAULT_HOST)
            port = instance.get('port', DEFAULT_PORT)
            user = instance.get('user')
            password = instance.get('pass')
            auth = '%s:%s@' % (user, password) if user and password else ''
            server = xmlrpclib.Server('http://%s%s:%s/RPC2' % (auth, host, port))
        return server.supervisor

    @staticmethod
    def _extract_uptime(proc):
        start, now = int(proc['start']), int(proc['now'])
        status = proc['statename']
        active_state = status in ['BACKOFF', 'RUNNING', 'STOPPING']
        return now - start if active_state else 0

    @staticmethod
    def _build_message(proc):
        start, stop, now = int(proc['start']), int(proc['stop']), int(proc['now'])
        proc['now_str'] = FORMAT_TIME(now)
        proc['start_str'] = FORMAT_TIME(start)
        proc['stop_str'] = '' if stop == 0 else FORMAT_TIME(stop)

        return """Current time: %(now_str)s
Process name: %(name)s
Process group: %(group)s
Description: %(description)s
Error log file: %(stderr_logfile)s
Stdout log file: %(stdout_logfile)s
Log file: %(logfile)s
State: %(statename)s
Start time: %(start_str)s
Stop time: %(stop_str)s
Exit Status: %(exitstatus)s""" % proc
