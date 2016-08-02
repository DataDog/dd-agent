"""
A Windows Service wrapper for win32/wsupervisor.py which consists in a minimalistic
supervisor for our agent with restart tries in case of failure. This program
will be packaged into an .exe file with py2exe in our omnibus build. It doesn't
have any project dependencies and shouldn't. It just launches and talks to our
Windows supervisor in our Python env. This way the agent code isn't shipped in
an .exe file which allows for easy hacking on it's source code.

Many thanks to the author of the article below which saved me quite some time:
http://ryrobes.com/python/running-python-scripts-as-a-windows-service/

"""
# stdlib
import os
import logging
import signal
import time

# 3p
import psutil
import win32api
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
        # Are we in a py2exed package or in a source install script or just a git pulled repo ?
        if not os.path.isfile(os.path.join(current_dir, 'windows_supervisor.py')):
            # py2exe package
            # current_dir should be somthing like
            # C:\Program Files(x86)\Datadog\Datadog Agent\dist\library.zip\win32s
            self.agent_path = os.path.join(current_dir, '..', '..', '..', 'agent')
        else:
            self.agent_path = os.path.join(current_dir, '..')
            # If we are in a proper source install script, let's get into the agent directory
            agent_dir = os.path.join(self.agent_path, 'agent')
            if os.path.isdir(agent_dir):
                self.agent_path = agent_dir

        self.agent_path = os.path.normpath(self.agent_path)
        logging.info("Agent path: {0}".format(self.agent_path))
        self.proc = None

    def SvcStop(self):
        """ Called when Windows wants to stop the service """
        if self._is_supervisor_alive():
            logging.info("Stopping supervisor...")
            # Soft termination based on TCP sockets to handle communication between the service
            # layer and the Windows supervisor
            self.proc.send_signal(signal.CTRL_C_EVENT)
            for _ in xrange(10):
                if self._is_supervisor_alive():
                    time.sleep(1)
                else:
                    break
            if self._is_supervisor_alive():
                # Ok some processes didn't want to die apparently, let's take care of them the hard
                # way !
                logging.warning("Killing supervisor and all agent processes")
                agent_processes = self.proc.children(recursive=True)

                self.proc.kill()
                for p in agent_processes:
                    p.kill()

            logging.info("All the agent processes stopped")
        else:
            logging.info('Supervisor is already stopped (or never started)')

        # We can quit quietly now
        win32event.SetEvent(self.h_wait_stop)
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)

    def SvcDoRun(self):
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, '')
        )

        # Let's start our components and put our supervisor's output into the
        # appropriate log file. This program also logs a minimalistic set of
        # lines in the same supervisor.log.

        logging.info("Starting Supervisor")

        # Since we don't call terminate here, the execution of the supervisord
        # will be performed in a non blocking way. If an error is triggered
        # here, tell windows we're closing the service and report accordingly
        try:
            logging.info("Changing working directory to \"{0}\"".format(self.agent_path))
            os.chdir(self.agent_path)

            # This allows us to use the system's Python in case there is no embedded python
            embedded_python = os.path.normpath(
                os.path.join(self.agent_path, '..', 'embedded', 'python.exe')
            )
            if not os.path.isfile(embedded_python):
                embedded_python = "python"

            self.proc = psutil.Popen([embedded_python, "windows_supervisor.py", "start", "server"])
        except WindowsError as e:
            logging.exception("WindowsError occured when starting our supervisor :\n\t"
                              "[Errno {1}] {0}".format(e.strerror, e.errno))
            self.SvcStop()
            return
        except Exception as e:
            logging.exception("[Error happened when launching the Windows supervisor] {0}".format(e.message))
            self.SvcStop()
            return

        logging.info("Supervisor started")

        # Let's wait for our user to send a sigkill. We can't have RunSvc exit
        # before we actually kill our subprocess (the while True is just a
        # paranoia check in case win32event.INFINITE isn't really... infinite)
        while True:
            rc = win32event.WaitForSingleObject(self.h_wait_stop, 1000)
            if rc == win32event.WAIT_OBJECT_0:
                logging.info("Service stop requested")
                break
            elif rc == win32event.WAIT_TIMEOUT and not self._is_supervisor_alive():
                self.SvcStop()
                break

        logging.info("Service stopped")

    def _is_supervisor_alive(self):
        return self.proc is not None and self.proc.is_running()


if __name__ == '__main__':
    # TODO: handle exe clicks and console commands other than install, start,
    # stop and uninstall (like jmxterm, flare, checkconfig...)
    # The below is to handle CTRL-C or CTRL-break in the console OR we don't
    # really need the console to be used on windows (do we?) so let's just don't
    # do anything here.
    win32api.SetConsoleCtrlHandler(lambda ctrlType: True, True)

    # And here we go !
    win32serviceutil.HandleCommandLine(AgentService)
