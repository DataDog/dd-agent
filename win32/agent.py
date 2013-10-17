# set up logging before importing any other components
from config import initialize_logging; initialize_logging('collector')

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

from optparse import Values
from checks.collector import Collector
from emitter import http_emitter
from win32.common import handle_exe_click
import dogstatsd
from ddagent import Application
from config import (get_config, set_win32_cert_path, get_system_stats,
    load_check_directory, get_win32service_file)
from win32.common import handle_exe_click
from pup import pup
from jmxfetch import JMXFetch

log = logging.getLogger(__name__)

class AgentSvc(win32serviceutil.ServiceFramework):
    _svc_name_ = "DatadogAgent"
    _svc_display_name_ = "Datadog Agent"
    _svc_description_ = "Sends metrics to Datadog"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        config = get_config(parse_args=False)
        self.forwarder = DDForwarder(config)
        self.dogstatsd = DogstatsdThread(config)
        self.pup = PupThread(config)

        # Setup the correct options so the agent will use the forwarder
        opts, args = Values({
            'dd_url': None,
            'clean': False,
            'use_forwarder': True,
            'disabled_dd': False
        }), []
        agentConfig = get_config(parse_args=False, options=opts)
        self.agent = DDAgent(agentConfig)

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)

        # Stop all services
        self.running = False
        self.forwarder.stop()
        self.agent.stop()
        self.dogstatsd.stop()
        self.pup.stop()
        

    def SvcDoRun(self):
        import servicemanager
        servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE, 
                servicemanager.PYS_SERVICE_STARTED,
                (self._svc_name_, ''))
        # Start all services
        self.forwarder.start()
        self.agent.start()
        self.dogstatsd.start()
        self.pup.start()

        # Loop to keep the service running since all DD services are
        # running in separate threads
        self.running = True
        while self.running:
            time.sleep(1)


class DDAgent(threading.Thread):
    def __init__(self, agentConfig):
        threading.Thread.__init__(self)
        self.config = agentConfig
        # FIXME: `running` flag should be handled by the service
        self.running = True

    def run(self):
        log.debug("Windows Service - Starting collector")
        emitters = self.get_emitters()
        systemStats = get_system_stats()
        self.collector = Collector(self.config, emitters, systemStats)

        # Load the checks.d checks
        checksd = load_check_directory(self.config)

        # Main agent loop will run until interrupted
        while self.running:
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

class DDForwarder(threading.Thread):
    def __init__(self, agentConfig):
        threading.Thread.__init__(self)
        set_win32_cert_path()
        self.config = get_config(parse_args = False)
        port = agentConfig.get('listen_port', 17123)
        if port is None:
            port = 17123
        else:
            port = int(port)
        self.port = port
        self.forwarder = Application(port, agentConfig, watchdog=False)

    def run(self):
        log.debug("Windows Service - Starting forwarder")
        self.forwarder.run()

    def stop(self):
        log.debug("Windows Service - Stopping forwarder")
        self.forwarder.stop()

class DogstatsdThread(threading.Thread):
    def __init__(self, agentConfig):
        threading.Thread.__init__(self)
        self.reporter, self.server, _ = dogstatsd.init(use_forwarder=True)

    def run(self):
        log.debug("Windows Service - Starting Dogstatsd server")
        self.reporter.start()
        self.server.start()

    def stop(self):
        log.debug("Windows Service - Stopping Dogstatsd server")
        self.server.stop()
        self.reporter.stop()
        self.reporter.join()

class PupThread(threading.Thread):
    def __init__(self, agentConfig):
        threading.Thread.__init__(self)
        self.config = agentConfig
        self.is_enabled = agentConfig.get('use_web_info_page', True)
        self.pup = pup

    def run(self):
        if self.is_enabled:
            log.debug("Windows Service - Starting Pup")
            self.pup.run_pup(self.config)

    def stop(self):
        if self.is_enabled:
            log.debug("Windows Service - Stopping Pup")
            self.pup.stop()

if __name__ == '__main__':
    if len(sys.argv) == 1:
        handle_exe_click(AgentSvc._svc_name_)
    else:
        win32serviceutil.HandleCommandLine(AgentSvc)
