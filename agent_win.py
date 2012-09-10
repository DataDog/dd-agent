import win32serviceutil
import win32service
import win32event
import servicemanager
import socket
import time

from config import get_config
from emitter import http_emitter
from checks.common import checks

class DDAgentSvc(win32serviceutil.ServiceFramework):
    _svc_name_ = "ddagent"
    _svc_display_name_ = "Datadog Agent"
    _svc_description_ = "Sends metrics to Datadog"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)

    def SvcStop(self):
        self.agent.stop()
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)

    def SvcDoRun(self):
        servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                                servicemanager.PYS_SERVICE_STARTED,
                                (self._svc_name_, ''))
        
        # Init the agent and start it
        self.agent = DDAgent(get_config(init_logging=True, parse_args=False))
        self.agent.run()

class DDAgent(object):
    def __init__(self, agentConfig):
        self.config = agentConfig
        # FIXME: `running` flag should be handled by the service
        self.running = True

    def run(self):
        emitters = self.get_emitters();
        chk = checks(self.config, emitters)

        # Main agent loop will run until interrupted
        firstRun = True
        while self.running:
            chk.doChecks(firstRun)
            firstRun=False
            time.sleep(self.config['check_freq'])

    def stop(self):
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

if __name__ == '__main__':
    win32serviceutil.HandleCommandLine(DDAgentSvc)