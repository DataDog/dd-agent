import win32serviceutil
import win32service
import win32event
import servicemanager
import logging
import threading
import sys

from config import get_config
from checks import gethostname
import dogstatsd
from win32.common import handle_exe_click

logger = logging.getLogger('dogstatsd')

class DogstatsdSvc(win32serviceutil.ServiceFramework):
    _svc_name_ = "dogstatsd"
    _svc_display_name_ = "DogstatsD"
    _svc_description_ = "A Statsd server for sending metrics to Datadog"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)

    def SvcStop(self):
        self.running = False
        self.reporter.end()

        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)
        raise SystemExit

    def SvcDoRun(self):
        servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                                servicemanager.PYS_SERVICE_STARTED,
                                (self._svc_name_, ''))
        self.reporter, self.server = dogstatsd.init()

        self.running = True
        while self.running:
            self.server.submit()

if __name__ == '__main__':
    if len(sys.argv) == 1:
        handle_exe_click(DogstatsdSvc._svc_name_)
    else:
        win32serviceutil.HandleCommandLine(DogstatsdSvc)