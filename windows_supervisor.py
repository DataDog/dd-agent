"""
A simple supervisor program written from scratch to run Datadog Agent. We couldn't
use supervisord on Windows since it relies on signals, poorly supported on Windows.
"""
# set up logging before importing any other components
from config import initialize_logging  # noqa
initialize_logging('supervisor')


# stdlib (other than sys and os)
import os
import sys
import time
import signal
import select
import socket
import psutil
import logging
import multiprocessing
from optparse import Values
from collections import deque

# win32
import win32api

# project
from config import (
    get_config,
)
from util import get_hostname
from utils.jmx import JMXFiles


log = logging.getLogger('supervisor')


SERVICE_SLEEP_INTERVAL = 1
MAX_FAILED_HEARTBEATS = 8  # runs of collector
DEFAULT_COLLECTOR_PROFILE_INTERVAL = 20


class AgentSupervisor():
    devnull = None

    def __init__(self, server=False):
        AgentSupervisor.devnull = open(os.devnull, 'w')

        config = get_config(parse_args=False)

        # Should we listen for killing requests on port 9001 ?
        self.server_mode = server

        # Setup the correct options so the agent will use the forwarder
        opts, args = Values({
            'autorestart': False,
            'dd_url': None,
            'use_forwarder': True,
            'disabled_dd': False,
            'profile': False
        }), []
        agent_config = get_config(parse_args=False, options=opts)
        self.hostname = get_hostname(agent_config)

        # Watchdog for Windows
        self._collector_heartbeat, self._collector_send_heartbeat = multiprocessing.Pipe(False)
        self._collector_failed_heartbeats = 0
        self._max_failed_heartbeats = \
            MAX_FAILED_HEARTBEATS * agent_config['check_freq'] / SERVICE_SLEEP_INTERVAL

        # Let's have an uptime counter
        self.start_ts = None

        # Watch JMXFetch restarts
        self._MAX_JMXFETCH_RESTARTS = 3
        self._count_jmxfetch_restarts = 0

        # This allows us to use the system's Python in case there is no embedded python
        embedded_python = '..\\embedded\\python.exe'
        if not os.path.isfile(embedded_python):
            embedded_python = "python"

        # Keep a list of running processes so we can start/end as needed.
        # Processes will start started in order and stopped in reverse order.
        self.procs = {
            'forwarder': ProcessWatchDog("forwarder",
                DDProcess("Forwarder", [embedded_python, "ddagent.py"])),
            'collector': ProcessWatchDog("collector",
                DDProcess("Collector", [embedded_python, "agent.py", "foreground",
                          "--use-local-forwarder"])),
            'dogstatsd': ProcessWatchDog("dogstatsd",
                DDProcess("Dogstatsd server", [embedded_python, "dogstatsd.py",
                          "--use-local-forwarder"],
                          config.get("use_dogstatsd", True))),
            'jmxfetch': ProcessWatchDog("jmxfetch",
                JMXFetchProcess("JMXFetch", [embedded_python, "jmxfetch.py"], 3)),
        }

    def stop(self):
        # Stop all services.
        log.info("Killing all the agent's primary processes.")
        self.running = False
        for proc in self.procs.values():
            proc.terminate()
        AgentSupervisor.devnull.close()

        # Let's log the uptime
        if self.start_ts is None:
            self.start_ts = time.time()
        time.sleep(SERVICE_SLEEP_INTERVAL*2)
        secs = int(time.time()-self.start_ts)
        mins = int(secs/60)
        hours = int(secs/3600)
        log.info("They're all dead! The agent has been run for {0} hours {1} "
                 "minutes {2} seconds".
                 format(hours, mins % 60, secs % 60))

    def run(self):
        self.start_ts = time.time()

        service_sock = None
        clients = []
        if(self.server_mode):
            service_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            service_sock.bind(('', 9001))
            service_sock.listen(1)

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
                    log.warning("%s has died. Restarting..." % name)
                    proc.restart()

            self._check_collector_blocked()

            if(self.server_mode):
                # Let's check if the service tried to connect to us
                rlist, wlist, xlist = select.select([service_sock], [], [],
                        SERVICE_SLEEP_INTERVAL/2.0)

                for req in rlist:
                    transaction, info = req.accept()
                    clients.append(transaction)

                requests = []
                try:
                    requests, wlist, xlist = select.select(clients, [], [],
                            SERVICE_SLEEP_INTERVAL/2.0)
                except select.error:
                    pass
                else:
                    for req in requests:
                        msg = req.recv(1024)
                        log.info("received message from Windows service layer : {0}".format(msg.decode()))
                        if msg.decode() == "die":
                            log.info("\"die\" received. Stopping all subprocesses...")
                            supervisor.stop()
                            log.info("Subprocesses have been stopped. Have a nice day !")
                        else:
                            time.sleep(SERVICE_SLEEP_INTERVAL)
            else:
                time.sleep(SERVICE_SLEEP_INTERVAL)

    def _check_collector_blocked(self):
        if self._collector_heartbeat.poll():
            while self._collector_heartbeat.poll():
                self._collector_heartbeat.recv()
            self._collector_failed_heartbeats = 0
        else:
            self._collector_failed_heartbeats += 1
            if self._collector_failed_heartbeats > self._max_failed_heartbeats:
                log.warning("%s was unresponsive for too long. Restarting..." % 'collector')
                self.procs['collector'].restart()
                self._collector_failed_heartbeats = 0


class ProcessWatchDog(object):
    """
    Monitor the attached process.
    Restarts when it exits until the limit set is reached.
    """
    DEFAULT_MAX_RESTARTS = 5
    _RESTART_TIMEFRAME = 3600

    def __init__(self, name, process, max_restarts=None):
        """
        :param max_restarts: maximum number of restarts per _RESTART_TIMEFRAME timeframe.
        """
        self._name = name
        self._process = process
        self._restarts = deque([])
        self._max_restarts = max_restarts or self.DEFAULT_MAX_RESTARTS

    def start(self):
        return self._process.start()

    def terminate(self):
        return self._process.terminate()

    def is_alive(self):
        return self._process.is_alive()

    def is_enabled(self):
        return self._process.is_enabled

    def _can_restart(self):
        now = time.time()
        while(self._restarts and self._restarts[0] < now - self._RESTART_TIMEFRAME):
            self._restarts.popleft()

        return len(self._restarts) < self._max_restarts

    def restart(self):
        if not self._can_restart():
            log.error(
                "{0} reached the limit of restarts ({1} tries during the last {2}s"
                " (max authorized: {3})). Not restarting..."
                .format(self._name, len(self._restarts),
                        self._RESTART_TIMEFRAME, self._max_restarts)
            )
            self._process.is_enabled = False
            return

        self._restarts.append(time.time())
        # Make a new proc instances because multiprocessing
        # won't let you call .start() twice on the same instance.
        if self._process.is_alive():
            self._process.terminate()

        self._process.start()

class DDProcess(object):
    def __init__(self, name, command, enable=True):
        self.name = name
        self.command = command
        self.is_enabled = enable
        self.proc = None

    def start(self):
        if self.is_enabled:
            log.info("Starting {0}".format(self.name))
            self.proc = psutil.Popen(self.command, stdout=AgentSupervisor.devnull, stderr=AgentSupervisor.devnull)
        else:
            log.info("{0} is not enabled, not starting it.".format(self.name))

    def stop(self):
        if self.proc is not None and self.proc.is_running():
            log.info("Stopping {0}".format(self.name))
            self.proc.terminate()

            psutil.wait_procs([self.proc], timeout=3)

            if self.proc.is_running():
                log.info("{0} doesn't want to exit. "
                         "Let's shoot him down".format(self.name))
                self.proc.kill()

            log.info("{0} is dead!".format(self.name))

    def terminate(self):
        self.stop()

    def is_alive(self):
        return self.proc is not None and self.proc.is_running()

    def is_enabled(self):
        return self.is_enabled


class JMXFetchProcess(DDProcess):
    def start(self):
        if self.is_enabled:
            JMXFiles.clean_exit_file()
            super(JMXFetchProcess, self).start()

    def stop(self):
        """
        Override `terminate` method to properly exit JMXFetch.
        """
        if self.proc is not None and self.proc.is_running():
            JMXFiles.write_exit_file()
            super(JMXFetchProcess, self).stop()


if __name__ == '__main__':
    multiprocessing.freeze_support()
    if len(sys.argv) < 2:
        # if the user forgot the start argument, let's just tell him
        print("To start the windows supervisor, please call the script with the `start` "
              "argument. Then just kill it with CTRL+C when you're done.")
        sys.exit(1)
    else:
        if sys.argv[1] == "start":
            log.info("Windows supervisor has just been started...")
            # Let's start our stuff and register a good old SIGINT callback
            if len(sys.argv) > 2 and sys.argv[2] == "server":
                supervisor = AgentSupervisor(True)
            else:
                supervisor = AgentSupervisor(False)

            def bye_bye(signum, frame):
                log.info("Stopping all subprocesses...")
                supervisor.stop()
                log.info("Have a nice day !")
                sys.exit(0)

            # Let's get ourselves some traditionnal ways to kill our supervisor
            signal.signal(signal.SIGINT, bye_bye)
            signal.signal(signal.SIGTERM, bye_bye)
            win32api.SetConsoleCtrlHandler(bye_bye, True)

            # Here we go !
            supervisor.run()
