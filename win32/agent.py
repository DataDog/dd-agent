# set up logging before importing any other components

import win32serviceutil
import win32service
import win32event
import win32evtlogutil
import sys
import logging
import tornado.httpclient
import threading
import modules
import time
import multiprocessing

from optparse import Values
from checks.collector import Collector
from emitter import http_emitter
from win32.common import handle_exe_click
import dogstatsd
from ddagent import Application
from config import (get_config, set_win32_cert_path, get_system_stats,
    load_check_directory, get_win32service_file)
from win32.common import handle_exe_click
from jmxfetch import JMXFetch
from util import get_hostname

log = logging.getLogger(__name__)
RESTART_INTERVAL = 24 * 60 * 60 # Defaults to 1 day

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
            'clean': False,
            'use_forwarder': True,
            'disabled_dd': False
        }), []
        agentConfig = get_config(parse_args=False, options=opts)
        self.hostname = get_hostname(agentConfig)
        self.restart_interval = \
            int(agentConfig.get('autorestart_interval', RESTART_INTERVAL))
        log.info("Autorestarting the collector ever %s seconds" % self.restart_interval)

        # Keep a list of running processes so we can start/end as needed.
        # Processes will start started in order and stopped in reverse order.
        self.procs = {
            'forwarder': DDForwarder(config, self.hostname),
            'collector': DDAgent(agentConfig, self.hostname),
            'dogstatsd': DogstatsdProcess(config, self.hostname),
        }

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)

        # Stop all services.
        self.running = False
        for proc in self.procs.values():
            proc.terminate()

    def SvcDoRun(self):
        import servicemanager
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
            if self.running:
                # Restart any processes that might have died.
                for name, proc in self.procs.iteritems():
                    if not proc.is_alive() and proc.is_enabled:
                        log.info("%s has died. Restarting..." % proc.name)
                        # Make a new proc instances because multiprocessing
                        # won't let you call .start() twice on the same instance.
                        new_proc = proc.__class__(proc.config, self.hostname)
                        new_proc.start()
                        self.procs[name] = new_proc
                # Auto-restart the collector if we've been running for a while.
                if time.time() - self.start_ts > self.restart_interval:
                    log.info('Auto-restarting collector after %s seconds' % self.restart_interval)
                    collector = self.procs['collector']
                    new_collector = collector.__class__(collector.config,
                                    self.hostname, start_event=False)
                    collector.terminate()
                    del self.procs['collector']
                    new_collector.start()

                    # Replace old process and reset timer.
                    self.procs['collector'] = new_collector
                    self.start_ts = time.time()

            time.sleep(1)


class DDAgent(multiprocessing.Process):
    def __init__(self, agentConfig, hostname, start_event=True):
        multiprocessing.Process.__init__(self, name='ddagent')
        self.config = agentConfig
        self.hostname = hostname
        self.start_event = start_event
        # FIXME: `running` flag should be handled by the service
        self.running = True
        self.is_enabled = True

    def run(self):
        from config import initialize_logging; initialize_logging('windows_collector')
        log.debug("Windows Service - Starting collector")
        emitters = self.get_emitters()
        systemStats = get_system_stats()
        self.collector = Collector(self.config, emitters, systemStats, self.hostname)

        # Load the checks.d checks
        checksd = load_check_directory(self.config, self.hostname)

        # Main agent loop will run until interrupted
        while self.running:
            self.collector.run(checksd=checksd, start_event=self.start_event)
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
        from config import initialize_logging; initialize_logging('windows_forwarder')
        log.debug("Windows Service - Starting forwarder")
        set_win32_cert_path()
        port = self.config.get('listen_port', 17123)
        if port is None:
            port = 17123
        else:
            port = int(port)
        app_config = get_config(parse_args = False)
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
        from config import initialize_logging; initialize_logging('windows_dogstatsd')
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

if __name__ == '__main__':
    multiprocessing.freeze_support()
    if len(sys.argv) == 1:
        handle_exe_click(AgentSvc._svc_name_)
    else:
        win32serviceutil.HandleCommandLine(AgentSvc)
