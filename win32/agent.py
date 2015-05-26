# stdlib
import logging
import modules
import multiprocessing
from optparse import Values
import servicemanager
import sys
import threading
import time
import tornado.httpclient
from win32.common import handle_exe_click
import win32event
import win32evtlogutil
import win32service
import win32serviceutil

# DD
from checks.collector import Collector
from config import (
    get_config,
    get_confd_path,
    get_system_stats,
    get_win32service_file,
    load_check_directory,
    set_win32_cert_path,
    PathNotFound,
)
import dogstatsd
from ddagent import Application
from emitter import http_emitter
from jmxfetch import JMXFetch
from util import get_hostname, get_os

log = logging.getLogger(__name__)

SERVICE_SLEEP_INTERVAL = 1
MAX_FAILED_HEARTBEATS = 8  # runs of collector


class AgentSvc(win32serviceutil.ServiceFramework):
    _svc_name_ = "DatadogAgent"
    _svc_display_name_ = "Datadog Agent"
    _svc_description_ = "Sends metrics to Datadog"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        config = get_config(parse_args=False)

        # Setup the correct options so the agent will use the forwarder
        opts, args = Values({
            'autorestart': False,
            'dd_url': None,
            'use_forwarder': True,
            'disabled_dd': False,
            'profile': False
        }), []
        agentConfig = get_config(parse_args=False, options=opts)
        self.hostname = get_hostname(agentConfig)

        # Watchdog for Windows
        self._collector_heartbeat, self._collector_send_heartbeat = multiprocessing.Pipe(False)
        self._collector_failed_heartbeats = 0
        self._max_failed_heartbeats = \
            MAX_FAILED_HEARTBEATS * agentConfig['check_freq'] / SERVICE_SLEEP_INTERVAL

        # Watch JMXFetch restarts
        self._MAX_JMXFETCH_RESTARTS = 3
        self._count_jmxfetch_restarts = 0

        # Keep a list of running processes so we can start/end as needed.
        # Processes will start started in order and stopped in reverse order.
        self.procs = {
            'forwarder': ProcessWatchDog("forwarder", DDForwarder(config, self.hostname)),
            'collector': ProcessWatchDog("collector", DDAgent(agentConfig, self.hostname,
                                         heartbeat=self._collector_send_heartbeat)),
            'dogstatsd': ProcessWatchDog("dogstatsd", DogstatsdProcess(config, self.hostname)),
            'jmxfetch': ProcessWatchDog("jmxfetch", JMXFetchProcess(config, self.hostname), 3),
        }

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)

        # Stop all services.
        self.running = False
        for proc in self.procs.values():
            proc.terminate()

    def SvcDoRun(self):
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, ''))
        self.start_ts = time.time()

        # Start all services.
        for proc in self.procs.values():
            proc.start()

        # Loop to keep the service running since all DD services are
        # running in separate processes
        self.running = True
        while self.running:
            # Restart any processes that might have died.
            for name, proc in self.procs.iteritems():
                if not proc.is_alive() and proc.is_enabled():
                    servicemanager.LogInfoMsg("%s has died. Restarting..." % name)
                    proc.restart()

            self._check_collector_blocked()

            time.sleep(SERVICE_SLEEP_INTERVAL)

    def _check_collector_blocked(self):
        if self._collector_heartbeat.poll():
            while self._collector_heartbeat.poll():
                self._collector_heartbeat.recv()
            self._collector_failed_heartbeats = 0
        else:
            self._collector_failed_heartbeats += 1
            if self._collector_failed_heartbeats > self._max_failed_heartbeats:
                servicemanager.LogInfoMsg(
                    "%s was unresponsive for too long. Restarting..." % 'collector')
                self.procs['collector'].restart()
                self._collector_failed_heartbeats = 0


class ProcessWatchDog(object):
    """
    Monitor the attached process.
    Restarts when it exits until the limit set is reached.
    """
    def __init__(self, name, process, max_restarts=5):
        self._name = name
        self._process = process
        self._count_restarts = 0
        self._MAX_RESTARTS = max_restarts

    def start(self):
        return self._process.start()

    def terminate(self):
        return self._process.terminate()

    def is_alive(self):
        return self._process.is_alive()

    def is_enabled(self):
        return self._process.is_enabled

    def restart(self):
        self._count_restarts += 1
        if self._count_restarts >= self._MAX_RESTARTS:
            servicemanager.LogInfoMsg(
                "%s reached the limit of restarts. Not restarting..." % self._name)
            self._process.is_enabled = False
            return

        # Make a new proc instances because multiprocessing
        # won't let you call .start() twice on the same instance.
        if self._process.is_alive():
            self._process.terminate()

        self._process = self._process.__class__(self._process.config, self._process.hostname)
        self._process.start()


class DDAgent(multiprocessing.Process):
    def __init__(self, agentConfig, hostname, heartbeat=None):
        multiprocessing.Process.__init__(self, name='ddagent')
        self.config = agentConfig
        self.hostname = hostname
        self._heartbeat = heartbeat
        # FIXME: `running` flag should be handled by the service
        self.running = True
        self.is_enabled = True

    def run(self):
        from config import initialize_logging
        initialize_logging('windows_collector')
        log.debug("Windows Service - Starting collector")
        emitters = self.get_emitters()
        systemStats = get_system_stats()
        self.collector = Collector(self.config, emitters, systemStats, self.hostname)

        # Load the checks.d checks
        checksd = load_check_directory(self.config, self.hostname)

        # Main agent loop will run until interrupted
        while self.running:
            if self._heartbeat:
                self._heartbeat.send(0)
            self.collector.run(checksd=checksd)
            time.sleep(self.config['check_freq'])

    def stop(self):
        log.debug("Windows Service - Stopping collector")
        self.collector.stop()
        if JMXFetch.is_running():
            JMXFetch.stop()
        self.running = False

    def get_emitters(self):
        emitters = [http_emitter]
        custom = [s.strip() for s in
            self.config.get('custom_emitters', '').split(',')]
        for emitter_spec in custom:
            if not emitter_spec:
                continue
            emitters.append(modules.load(emitter_spec, 'emitter'))

        return emitters


class DDForwarder(multiprocessing.Process):
    def __init__(self, agentConfig, hostname):
        multiprocessing.Process.__init__(self, name='ddforwarder')
        self.config = agentConfig
        self.is_enabled = True
        self.hostname = hostname

    def run(self):
        from config import initialize_logging
        initialize_logging('windows_forwarder')
        log.debug("Windows Service - Starting forwarder")
        set_win32_cert_path()
        port = self.config.get('listen_port', 17123)
        if port is None:
            port = 17123
        else:
            port = int(port)
        app_config = get_config(parse_args=False)
        self.forwarder = Application(port, app_config, watchdog=False)
        try:
            self.forwarder.run()
        except Exception:
            log.exception("Uncaught exception in the forwarder")

    def stop(self):
        log.debug("Windows Service - Stopping forwarder")
        self.forwarder.stop()


class DogstatsdProcess(multiprocessing.Process):
    def __init__(self, agentConfig, hostname):
        multiprocessing.Process.__init__(self, name='dogstatsd')
        self.config = agentConfig
        self.is_enabled = self.config.get('use_dogstatsd', True)
        self.hostname = hostname

    def run(self):
        from config import initialize_logging
        initialize_logging('windows_dogstatsd')
        if self.is_enabled:
            log.debug("Windows Service - Starting Dogstatsd server")
            self.reporter, self.server, _ = dogstatsd.init(use_forwarder=True)
            self.reporter.start()
            self.server.start()
        else:
            log.info("Dogstatsd is not enabled, not starting it.")

    def stop(self):
        if self.is_enabled:
            log.debug("Windows Service - Stopping Dogstatsd server")
            self.server.stop()
            self.reporter.stop()
            self.reporter.join()


class JMXFetchProcess(multiprocessing.Process):
    def __init__(self, agentConfig, hostname):
        multiprocessing.Process.__init__(self, name='jmxfetch')
        self.config = agentConfig
        self.hostname = hostname

        try:
            osname = get_os()
            confd_path = get_confd_path(osname)
            self.jmx_daemon = JMXFetch(confd_path, agentConfig)
            self.jmx_daemon.configure()
            self.is_enabled = self.jmx_daemon.should_run()

        except PathNotFound:
            self.is_enabled = False

    def run(self):
        if self.is_enabled:
            self.jmx_daemon.run()

    def stop(self):
        pass


if __name__ == '__main__':
    multiprocessing.freeze_support()
    if len(sys.argv) == 1:
        handle_exe_click(AgentSvc._svc_name_)
    else:
        win32serviceutil.HandleCommandLine(AgentSvc)
