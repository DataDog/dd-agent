"""
A Windows Service wrapper for win32/agent.py which consists in a minimalistic
supervisor for our agent with restart tries in case of failure. This program
will be packaged into an .exe file with py2exe in our omnibus build. It doesn't
have any project dependencies and shouldn't. It just launches and talks to our
Windows supervisor in our Python venv. This way the agent code isn't shipped in
an .exe file which allows for easy hacking on it's source code.

Many thanks to the author of the article below which saved me quite some time:
http://ryrobes.com/python/running-python-scripts-as-a-windows-service/

"""

# 3p
import os
import time

import win32api
import subprocess
import win32event
import win32service
import win32serviceutil
import servicemanager


def _windows_commondata_path():
    """Return the common appdata path, using ctypes
    From http://stackoverflow.com/questions/626796/\
    how-do-i-find-the-windows-common-application-data-folder-using-python
    """
    import ctypes
    from ctypes import wintypes, windll

    CSIDL_COMMON_APPDATA = 35

    _SHGetFolderPath = windll.shell32.SHGetFolderPathW
    _SHGetFolderPath.argtypes = [wintypes.HWND,
                                ctypes.c_int,
                                wintypes.HANDLE,
                                wintypes.DWORD, wintypes.LPCWSTR]

    path_buf = wintypes.create_unicode_buffer(wintypes.MAX_PATH)
    result = _SHGetFolderPath(0, CSIDL_COMMON_APPDATA, 0, 0, path_buf)
    return path_buf.value


class AgentService(win32serviceutil.ServiceFramework):
    _svc_name_ = "DatadogAgent"
    _svc_display_name_ = "Datadog Agent"
    _svc_description_ = "Sends metrics to Datadog"

    # We use stock windows events to leverage windows capabilities to wait for
    # events to be triggered. It's a bit cleaner than a `while !self.stop_requested`
    # in our services SvcRun() loop :)
    # Oh and btw, h stands for "HANDLE", a common concept in the win32 C API
    h_wait_stop = win32event.CreateEvent(None, 0, 0, None)

    def __init__(self, args):

        win32serviceutil.ServiceFramework.__init__(self, args)

        self.log_path = os.path.join(_windows_commondata_path(), 'Datadog', 'logs', 'service.log')
        self.supervisor_log_path = os.path.join(_windows_commondata_path(), 'Datadog', 'logs', 'supervisor.log')

        self.agent_path = os.path.dirname(os.path.realpath(__file__)) + "\\supervisor.py'

    def SvcStop(self):
        """ Called when Windows wants to stop the service """
        win32event.SetEvent(self.h_wait_stop)
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)

    def SvcDoRun(self):
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, ''))

        # Let's start our components and put our supervisor's output into the
        # appropriate log file. This program also logs a minimalistic set of
        # lines in the same supervisor.log.

        log_pipe = open(self.supervisor_log_path, 'a')
        self.log("Starting Supervisor!")
        self.log(os.getcwd())

        # Since we don't call terminate here, the execution of the supervisord
        # will be performed in a non blocking way. If an error is triggered
        # here, tell windows we're closing the service and report accordingly
        try:
            proc = subprocess.Popen(["python", self.agent_path , "start"],
                stdout=log_pipe, stderr=log_pipe)
        except WindowsError as e:
            self.log("WindowsError occured when starting our supervisor :\n\t"
                     "[Errno {1}] {0}".
                     format(e.strerror, e.errno))
            self.SvcStop()
            return
        except Exception as e:
            self.log("[Error happened when launching the Windows supervisor] {0}".
                     format(e.message))
            self.SvcStop()
            return

        # Let's wait for our user to send a sigkill. We can't have RunSvc exit
        # before we actually kill our subprocess (the while True is just a
        # paranoia check in case win32event.INFINITE isn't really... infinite)
        while True:
            rc = win32event.WaitForSingleObject(self.h_wait_stop, win32event.INFINITE)
            if rc == win32event.WAIT_OBJECT_0:
                self.log("Service stop requested")
                break

        # Happy endings
        self.log("Killing supervisor")
        proc.terminate()
        self.log("Supervisor killed")
        log_pipe.close()

    def log(self, msg):
        with open(self.log_path, 'a') as logfile:
            logfile.write("[{0}] ddagent.exe - {1} \n\n".
                          format(time.strftime("%H:%M:%S"), msg))


if __name__ == '__main__':
    # TODO: handle exe clicks and console commands other than install, start,
    # stop and uninstall (like jmxterm, flare, checkconfig...)
    # The below is to handle CTRL-C or CTRL-break in the console OR we don't
    # really need the console to be used on windows (do we?) so let's just don't
    # do anything here.
    win32api.SetConsoleCtrlHandler(lambda ctrlType: True, True)

    # Let's handle traditionnal SIGTERMs in case we're killing the pythonservice.exe
    # process from the task manager... a common operation on Windows :)
    def bye_bye():
        win32event.SetEvent(AgentService.h_wait_stop)

    win32api.SetConsoleCtrlHandler(bye_bye, True)

    # And here we go !
    win32serviceutil.HandleCommandLine(AgentService)
