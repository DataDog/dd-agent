import win32serviceutil
import win32service
import win32event
import servicemanager
import socket
from tornado.options import define, parse_command_line, options

from ddagent import Application
from config import get_config

class DDForwarderSvc(win32serviceutil.ServiceFramework):
    _svc_name_ = "ddforwarder"
    _svc_display_name_ = "Datadog Forwarder"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)

    def SvcStop(self):
        self.app.stop()
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)

    def SvcDoRun(self):
        servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                                servicemanager.PYS_SERVICE_STARTED,
                                (self._svc_name_, ''))

        agentConfig = get_config(parse_args = False)
        port = agentConfig.get('listen_port', 17123)
        if port is None:
            port = 17123
        else:
            port = int(port)

        self.app = Application(port, agentConfig, watchdog=False)
        self.app.run()

if __name__ == '__main__':
    win32serviceutil.HandleCommandLine(DDForwarderSvc)