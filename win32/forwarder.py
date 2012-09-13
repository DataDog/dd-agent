import win32serviceutil
import win32service
import win32event
import servicemanager
import sys
import tornado.httpclient

import ddagent
from config import get_config, set_win32_cert_path
from win32.common import handle_exe_click

class DDForwarderSvc(win32serviceutil.ServiceFramework):
    _svc_name_ = "ddforwarder"
    _svc_display_name_ = "Datadog Forwarder"
    _svc_description_ = "Buffers metrics from the agent and forwards them to Datadog"

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

        set_win32_cert_path()
        app = ddagent.init()
        app.run()

if __name__ == '__main__':
    if len(sys.argv) == 1:
        handle_exe_click(DDForwarderSvc._svc_name_)
    else:
        win32serviceutil.HandleCommandLine(DDForwarderSvc)