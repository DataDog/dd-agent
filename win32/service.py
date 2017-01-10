"""
A Windows Service wrapper for win32/windows_supervisor.py which consists in a minimalistic
Supervisor for our agent with restart tries in case of failure. This program
will be packaged into an .exe file with py2exe in our omnibus build. It doesn't
have any project dependencies and shouldn't. It just launches and talks to our
Windows Supervisor in our Python env. This way the agent code isn't shipped in
an .exe file which allows for easy hacking on it's source code.

Many thanks to the author of the article below which saved me quite some time:
http://ryrobes.com/python/running-python-scripts-as-a-windows-service/

"""
# stdlib
import os
import socket
import select
import logging

# 3p
import psutil
import win32event
import win32service
import win32serviceutil
import servicemanager

import ctypes
from ctypes import wintypes, windll


def _windows_commondata_path():
    """Return the common appdata path, using ctypes
    From http://stackoverflow.com/questions/626796/\
    how-do-i-find-the-windows-common-application-data-folder-using-python
    """
    CSIDL_COMMON_APPDATA = 35

    _SHGetFolderPath = windll.shell32.SHGetFolderPathW
    _SHGetFolderPath.argtypes = [wintypes.HWND,
                                 ctypes.c_int,
                                 wintypes.HANDLE,
                                 wintypes.DWORD, wintypes.LPCWSTR]

    path_buf = wintypes.create_unicode_buffer(wintypes.MAX_PATH)
    _SHGetFolderPath(0, CSIDL_COMMON_APPDATA, 0, 0, path_buf)
    return path_buf.value


# Let's configure logging accordingly now (we need the above function for that)
logging.basicConfig(
    filename=os.path.join(_windows_commondata_path(), 'Datadog', 'logs', 'service.log'),
    level=logging.DEBUG,
    format='%(asctime)s | %(levelname)s | %(name)s(%(filename)s:%(lineno)s) | %(message)s'
)


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

        current_dir = os.path.dirname(os.path.realpath(__file__))
        # py2exe package
        # current_dir should be somthing like
        # C:\Program Files(x86)\Datadog\Datadog Agent\dist\library.zip\win32s
        self.agent_path = os.path.join(current_dir, '..', '..', '..', 'agent')

        self.agent_path = os.path.normpath(self.agent_path)
        logging.debug("Agent path: {0}".format(self.agent_path))
        self.proc = None

    def SvcStop(self):
        """ Called when Windows wants to stop the service """
        # Not even started
        if self.proc is None:
            logging.info('Supervisor was not yet started, stopping now.')
        # Started, and died
        elif not self.proc.is_running():
            logging.info('Supervisor already exited. Some processes may still be alive. Stopping now.')
        # Still running
        else:
            logging.info("Stopping Supervisor...")
            # Soft termination based on TCP sockets to handle communication between the service
            # layer and the Windows Supervisor
            supervisor_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            supervisor_sock.connect(('localhost', 9001))

            supervisor_sock.send("die".encode())

            rlist, wlist, xlist = select.select([supervisor_sock], [], [], 15)
            if not rlist:
                # Ok some processes didn't want to die apparently, let's take care og them the hard
                # way !
                logging.warning("Some processes are still alive. Killing them.")
                parent = psutil.Process(self.proc.pid)
                children = parent.children(recursive=True)

                for p in [parent] + children:
                    p.kill()

            logging.info("Supervisor and its children processes exited, stopping now.")

        # We can sleep quietly now
        win32event.SetEvent(self.h_wait_stop)
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)

    def SvcDoRun(self):
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, '')
        )

        # Let's start our components and put our Supervisor's output into the
        # appropriate log file. This program also logs a minimalistic set of
        # lines in the same supervisor.log.

        logging.info("Starting Supervisor.")

        # Since we don't call terminate here, the execution of the supervisord
        # will be performed in a non blocking way. If an error is triggered
        # here, tell windows we're closing the service and report accordingly
        try:
            logging.debug('Changing working directory to "%s".', self.agent_path)
            os.chdir(self.agent_path)

            # This allows us to use the system's Python in case there is no embedded python
            embedded_python = os.path.normpath(
                os.path.join(self.agent_path, '..', 'embedded', 'python.exe')
            )
            if not os.path.isfile(embedded_python):
                embedded_python = "python"

            self.proc = psutil.Popen([embedded_python, "windows_supervisor.py", "start", "server"])
        except Exception:
            logging.exception("Error when launching Supervisor")
            self.SvcStop()
            return

        logging.info("Supervisor started.")

        # Let's wait for our user to send a sigkill. We can't have RunSvc exit
        # before we actually kill our subprocess (the while True is just a
        # paranoia check in case win32event.INFINITE isn't really... infinite)
        while True:
            rc = win32event.WaitForSingleObject(self.h_wait_stop, win32event.INFINITE)
            if rc == win32event.WAIT_OBJECT_0:
                logging.info("Service stop requested.")
                break

        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STOPPED,
            (self._svc_name_, '')
        )
        logging.info("Service stopped.")


if __name__ == '__main__':
    # handle install, start, stop and uninstall
    win32serviceutil.HandleCommandLine(AgentService)
