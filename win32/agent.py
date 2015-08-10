# stdlib
from collections import deque
import logging
import multiprocessing
from optparse import Values
import sys
import time

# win32 (yeah that's a pity but we need that to handle sigterms)
import win32api

# TODO: dogstatsd and the collector are still up when our guy here is killed...
# Investigate this !

# project
from win32.common import handle_exe_click
from checks.collector import Collector
from config import (
    get_confd_path,
    get_config,
    get_system_stats,
    load_check_directory,
    PathNotFound,
    set_win32_cert_path,
    set_win32_requests_ca_bundle_path,
)
from ddagent import Application
import dogstatsd
from emitter import http_emitter
from jmxfetch import JMXFetch
import modules
from util import get_hostname
from utils.jmx import JMXFiles
from utils.profile import AgentProfiler

log = logging.getLogger(__name__)

SERVICE_SLEEP_INTERVAL = 1
MAX_FAILED_HEARTBEATS = 8  # runs of collector
DEFAULT_COLLECTOR_PROFILE_INTERVAL = 20


class AgentSupervisor():
    def __init__(self):
        config = get_config(parse_args=False)

        # Setup the correct options so the agent will use the forwarder
        opts, args = Values({
            'autorestart': False,
            'dd_url': None,
            'use_forwarder': True,
            'disabled_dd': False,
            'profile': False
        }), []
        agentConfig = get_config(parse_args=False, options=opts)
        self.hostname = get_hostname(agentConfig)

        # Watchdog for Windows
        self._collector_heartbeat, self._collector_send_heartbeat = multiprocessing.Pipe(False)
        self._collector_failed_heartbeats = 0
        self._max_failed_heartbeats = \
            MAX_FAILED_HEARTBEATS * agentConfig['check_freq'] / SERVICE_SLEEP_INTERVAL

        # Watch JMXFetch restarts
        self._MAX_JMXFETCH_RESTARTS = 3
        self._count_jmxfetch_restarts = 0

        # Keep a list of running processes so we can start/end as needed.
        # Processes will start started in order and stopped in reverse order.
        self.procs = {
            'forwarder': ProcessWatchDog("forwarder", DDForwarder(config, self.hostname)),
            'collector': ProcessWatchDog("collector", DDAgent(agentConfig, self.hostname,
                                         heartbeat=self._collector_send_heartbeat)),
            'dogstatsd': ProcessWatchDog("dogstatsd", DogstatsdProcess(config, self.hostname)),
            'jmxfetch': ProcessWatchDog("jmxfetch", JMXFetchProcess(config, self.hostname), 3),
        }

    def stop(self):
        # Stop all services.
        self.running = False
        for proc in self.procs.values():
            proc.terminate()

    def run(self):
        self.start_ts = time.time()

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
                    print("%s has died. Restarting..." % name)
                    proc.restart()

            self._check_collector_blocked()

            time.sleep(SERVICE_SLEEP_INTERVAL)

    def _check_collector_blocked(self):
        if self._collector_heartbeat.poll():
            while self._collector_heartbeat.poll():
                self._collector_heartbeat.recv()
            self._collector_failed_heartbeats = 0
        else:
            self._collector_failed_heartbeats += 1
            if self._collector_failed_heartbeats > self._max_failed_heartbeats:
                print("%s was unresponsive for too long. Restarting..." % 'collector')
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
            print(
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

        # Recreate a new process
        self._process = self._process.__class__(
            self._process.config, self._process.hostname,
            **self._process.options
        )

        self._process.start()


class DDAgent(multiprocessing.Process):
    def __init__(self, agentConfig, hostname, **options):
        multiprocessing.Process.__init__(self, name='ddagent')
        self.config = agentConfig
        self.hostname = hostname
        self.options = options
        self._heartbeat = options.get('heartbeat')
        # FIXME: `running` flag should be handled by the service
        self.running = True
        self.is_enabled = True

    def run(self):
        from config import initialize_logging
        initialize_logging('windows_collector')
        log.debug("Windows Service - Starting collector")
        set_win32_requests_ca_bundle_path()
        emitters = self.get_emitters()
        systemStats = get_system_stats()
        self.collector = Collector(self.config, emitters, systemStats, self.hostname)

        in_developer_mode = self.config.get('developer_mode')

        # In developer mode, the number of runs to be included in a single collector profile
        collector_profile_interval = self.config.get('collector_profile_interval',
                                                     DEFAULT_COLLECTOR_PROFILE_INTERVAL)
        profiled = False
        collector_profiled_runs = 0

        # Load the checks.d checks
        checksd = load_check_directory(self.config, self.hostname)

        # Main agent loop will run until interrupted
        while self.running:
            if self._heartbeat:
                self._heartbeat.send(0)

            if in_developer_mode and not profiled:
                try:
                    profiler = AgentProfiler()
                    profiler.enable_profiling()
                    profiled = True
                except Exception as e:
                    log.warn("Cannot enable profiler: %s" % str(e))

            self.collector.run(checksd=checksd)

            if profiled:
                if collector_profiled_runs >= collector_profile_interval:
                    try:
                        profiler.disable_profiling()
                        profiled = False
                        collector_profiled_runs = 0
                    except Exception as e:
                        log.warn("Cannot disable profiler: %s" % str(e))
                else:
                    collector_profiled_runs += 1

            time.sleep(self.config['check_freq'])

    def stop(self):
        log.debug("Windows Service - Stopping collector")
        self.collector.stop()
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
    def __init__(self, agentConfig, hostname, **options):
        multiprocessing.Process.__init__(self, name='ddforwarder')
        self.config = agentConfig
        self.is_enabled = True
        self.hostname = hostname
        self.options = options

    def run(self):
        from config import initialize_logging
        initialize_logging('windows_forwarder')
        log.debug("Windows Service - Starting forwarder")
        set_win32_cert_path()
        port = self.config.get('listen_port', 17123)
        if port is None:
            port = 17123
        else:
            port = int(port)
        app_config = get_config(parse_args=False)
        self.forwarder = Application(port, app_config, watchdog=False)
        try:
            self.forwarder.run()
        except Exception:
            log.exception("Uncaught exception in the forwarder")

    def stop(self):
        log.debug("Windows Service - Stopping forwarder")
        self.forwarder.stop()


class DogstatsdProcess(multiprocessing.Process):
    def __init__(self, agentConfig, hostname, **options):
        multiprocessing.Process.__init__(self, name='dogstatsd')
        self.config = agentConfig
        self.is_enabled = self.config.get('use_dogstatsd', True)
        self.hostname = hostname
        self.options = options

    def run(self):
        from config import initialize_logging
        initialize_logging('windows_dogstatsd')
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


class JMXFetchProcess(multiprocessing.Process):
    def __init__(self, agentConfig, hostname, **options):
        multiprocessing.Process.__init__(self, name='jmxfetch')
        self.config = agentConfig
        self.hostname = hostname
        self.options = options

        try:
            confd_path = get_confd_path()
            self.jmx_daemon = JMXFetch(confd_path, agentConfig)
            self.jmx_daemon.configure()
            self.is_enabled = self.jmx_daemon.should_run()

        except PathNotFound:
            self.is_enabled = False

    def run(self):
        from config import initialize_logging
        initialize_logging('jmxfetch')
        if self.is_enabled:
            log.debug("Windows Service - Starting JMXFetch")
            JMXFiles.clean_exit_file()
            self.jmx_daemon.run()
        else:
            log.info("Windows Service - Not starting JMXFetch: no valid configuration found")

    def terminate(self):
        """
        Override `terminate` method to properly exit JMXFetch.
        """
        JMXFiles.write_exit_file()
        self.join()


if __name__ == '__main__':
    multiprocessing.freeze_support()
    if len(sys.argv) == 1:
        handle_exe_click("Datadog-Agent Windows service")
        pass
    else:
        if sys.argv[1] == "start":
            # Let's start our stuff and register a good old SINGINT callback
            supervisor = AgentSupervisor()

            def bye_bye():
                print("salut les pds !")
                supervisor.stop()

            win32api.SetConsoleCtrlHandler(bye_bye, True)

            # Here we go !
            supervisor.run()
