#!/opt/datadog-agent/embedded/bin/python
"""
    Datadog
    www.datadoghq.com
    ----
    Cloud-Scale Monitoring. Monitoring that tracks your dynamic infrastructure.

    Licensed under Simplified BSD License (see LICENSE)
    (C) Boxed Ice 2010 all rights reserved
    (C) Datadog, Inc. 2010-2016 all rights reserved
"""
# set up logging before importing any other components
from config import get_version, initialize_logging  # noqa
initialize_logging('collector')

# stdlib
import logging
import os
import signal
import sys
import time

# For pickle & PID files, see issue 293
os.umask(022)

# project
from checks.check_status import CollectorStatus
from checks.collector import Collector
from config import (
    get_config,
    get_parsed_args,
    get_system_stats,
    load_check_directory,
)
from emitter import http_emitter
from util import (
    EC2,
    get_hostname,
    Watchdog,
)
from utils.agent_process import AgentProcess
from utils.flare import Flare
from utils.configcheck import configcheck, sd_configcheck
from utils.jmx import jmx_command
from utils.pidfile import PidFile
from utils.profile import AgentProfiler
from utils.service_discovery.config_stores import get_config_store
from utils.service_discovery.sd_backend import get_sd_backend

# Constants
PID_NAME = "dd-agent"
PID_DIR = None
WATCHDOG_MULTIPLIER = 10
RESTART_INTERVAL = 4 * 24 * 60 * 60  # Defaults to 4 days
DEFAULT_COLLECTOR_PROFILE_INTERVAL = 20

# Globals
log = logging.getLogger('collector')


class Agent(AgentProcess):
    """
    The agent class is a process that runs the collector in foreground.
    """

    def __init__(self, pidfile, start_event=True, in_developer_mode=False):
        AgentProcess.__init__(self, pidfile)
        self.run_forever = True
        self.collector = None
        self.start_event = start_event
        self.in_developer_mode = in_developer_mode
        self._agentConfig = {}
        self._checksd = []
        self.collector_profile_interval = DEFAULT_COLLECTOR_PROFILE_INTERVAL
        self.check_frequency = None
        self.reload_configs_flag = False
        self.sd_backend = None

    def _handle_sigterm(self, signum, frame):
        """Handles SIGTERM and SIGINT, which gracefully stops the agent."""
        log.debug("Caught sigterm. Stopping run loop.")
        self.run_forever = False

        if self.collector:
            self.collector.stop()
        log.debug("Collector is stopped.")

    def _handle_sigusr1(self, signum, frame):
        """Handles SIGUSR1, which signals an exit with an autorestart."""
        self._handle_sigterm(signum, frame)
        self._do_restart()

    def _handle_sighup(self, signum, frame):
        """Handles SIGHUP, which signals a configuration reload."""
        log.info("SIGHUP caught! Scheduling configuration reload before next collection run.")
        self.reload_configs_flag = True

    def reload_configs(self):
        """Reloads the agent configuration and checksd configurations."""
        log.info("Attempting a configuration reload...")

        # Stop checks
        for check in self._checksd.get('initialized_checks', []):
            check.stop()

        # Reload checksd configs
        hostname = get_hostname(self._agentConfig)
        self._checksd = load_check_directory(self._agentConfig, hostname)

        # Logging
        num_checks = len(self._checksd['initialized_checks'])
        if num_checks > 0:
            log.info("Successfully reloaded {num_checks} checks".
                     format(num_checks=num_checks))
        else:
            log.info("No checksd configs found")

    @classmethod
    def info(cls, verbose=None):
        logging.getLogger().setLevel(logging.ERROR)
        return CollectorStatus.print_latest_status(verbose=verbose)

    def run(self, config=None):
        """Main loop of the collector"""

        # Gracefully exit on sigterm.
        signal.signal(signal.SIGTERM, self._handle_sigterm)

        # A SIGUSR1 signals an exit with an autorestart
        signal.signal(signal.SIGUSR1, self._handle_sigusr1)

        # Handle Keyboard Interrupt
        signal.signal(signal.SIGINT, self._handle_sigterm)

        # A SIGHUP signals a configuration reload
        signal.signal(signal.SIGHUP, self._handle_sighup)

        # Save the agent start-up stats.
        CollectorStatus().persist()

        # Intialize the collector.
        if not config:
            config = get_config(parse_args=True)

        self._agentConfig = self._set_agent_config_hostname(config)
        hostname = get_hostname(self._agentConfig)
        systemStats = get_system_stats(
            proc_path=self._agentConfig.get('procfs_path', '/proc').rstrip('/')
        )
        emitters = self._get_emitters()

        # Initialize service discovery
        if self._agentConfig.get('service_discovery'):
            self.sd_backend = get_sd_backend(self._agentConfig)

        # Load the checks.d checks
        self._checksd = load_check_directory(self._agentConfig, hostname)

        # Initialize the Collector
        self.collector = Collector(self._agentConfig, emitters, systemStats, hostname)

        # In developer mode, the number of runs to be included in a single collector profile
        self.collector_profile_interval = self._agentConfig.get('collector_profile_interval',
                                                                DEFAULT_COLLECTOR_PROFILE_INTERVAL)

        # Configure the watchdog.
        self.check_frequency = int(self._agentConfig['check_freq'])
        watchdog = self._get_watchdog(self.check_frequency)

        # Initialize the auto-restarter
        self.restart_interval = int(self._agentConfig.get('restart_interval', RESTART_INTERVAL))
        self.agent_start = time.time()

        profiled = False
        collector_profiled_runs = 0

        # Run the main loop.
        while self.run_forever:
            # Setup profiling if necessary
            if self.in_developer_mode and not profiled:
                try:
                    profiler = AgentProfiler()
                    profiler.enable_profiling()
                    profiled = True
                except Exception as e:
                    log.warn("Cannot enable profiler: %s" % str(e))

            if self.reload_configs_flag:
                self.reload_configs()

            # Do the work. Pass `configs_reloaded` to let the collector know if it needs to
            # look for the AgentMetrics check and pop it out.
            self.collector.run(checksd=self._checksd,
                               start_event=self.start_event,
                               configs_reloaded=self.reload_configs_flag)

            self.reload_configs_flag = False

            # Look for change in the config template store.
            # The self.sd_backend.reload_check_configs flag is set
            # to True if a config reload is needed.
            if self._agentConfig.get('service_discovery') and self.sd_backend and \
               not self.sd_backend.reload_check_configs:
                try:
                    self.sd_backend.reload_check_configs = get_config_store(
                        self._agentConfig).crawl_config_template()
                except Exception as e:
                    log.warn('Something went wrong while looking for config template changes: %s' % str(e))

            # Check if we should run service discovery
            # The `reload_check_configs` flag can be set through the docker_daemon check or
            # using ConfigStore.crawl_config_template
            if self._agentConfig.get('service_discovery') and self.sd_backend and \
               self.sd_backend.reload_check_configs:
                self.reload_configs_flag = True
                self.sd_backend.reload_check_configs = False

            if profiled:
                if collector_profiled_runs >= self.collector_profile_interval:
                    try:
                        profiler.disable_profiling()
                        profiled = False
                        collector_profiled_runs = 0
                    except Exception as e:
                        log.warn("Cannot disable profiler: %s" % str(e))

            # Only plan for next loop if we will continue, otherwise exit quickly.
            if self.run_forever:
                if watchdog:
                    watchdog.reset()
                if profiled:
                    collector_profiled_runs += 1
                log.debug("Sleeping for {0} seconds".format(self.check_frequency))
                time.sleep(self.check_frequency)

        # Now clean-up.
        try:
            CollectorStatus.remove_latest_status()
        except Exception:
            pass

        # Explicitly kill the process.
        log.info("Exiting. Bye bye.")
        sys.exit(0)

    def _get_emitters(self):
        return [http_emitter]

    def _get_watchdog(self, check_freq):
        watchdog = None
        if self._agentConfig.get("watchdog", True):
            watchdog = Watchdog(check_freq * WATCHDOG_MULTIPLIER,
                                max_mem_mb=self._agentConfig.get('limit_memory_consumption', None))
            watchdog.reset()
        return watchdog

    def _set_agent_config_hostname(self, agentConfig):
        # Try to fetch instance Id from EC2 if not hostname has been set
        # in the config file.
        # DEPRECATED
        if agentConfig.get('hostname') is None and agentConfig.get('use_ec2_instance_id'):
            instanceId = EC2.get_instance_id(agentConfig)
            if instanceId is not None:
                log.info("Running on EC2, instanceId: %s" % instanceId)
                agentConfig['hostname'] = instanceId
            else:
                log.info('Not running on EC2, using hostname to identify this server')
        return agentConfig

    def _do_restart(self):
        log.info("Running an auto-restart.")
        if self.collector:
            self.collector.stop()
        sys.exit(0)


def main():
    options, args = get_parsed_args()
    agentConfig = get_config(options=options)
    hostname = get_hostname(agentConfig)
    in_developer_mode = agentConfig.get('developer_mode')
    COMMANDS_AGENT = [
        'foreground',
    ]

    OLD_COMMANDS_AGENT = [
        'restart'
        'start',
        'status',
        'stop',
    ]

    COMMANDS_NO_AGENT = [
        'info',
        'check',
        'configcheck',
        'jmx',
        'flare',
    ]

    COMMANDS = COMMANDS_AGENT + COMMANDS_NO_AGENT

    if len(args) < 1:
        sys.stderr.write("Usage: %s %s\n" % (sys.argv[0], "|".join(COMMANDS)))
        return 2

    command = args[0]
    # Deprecation notice
    if command in OLD_COMMANDS_AGENT:
        from utils.deprecations import deprecate_old_command_line_tools
        deprecate_old_command_line_tools()
        return 1

    if command not in COMMANDS:
        sys.stderr.write("Unknown command: %s\n" % command)
        return 3

    if command in COMMANDS_AGENT:
        log.info('Agent version %s' % get_version())
        agent = Agent(PidFile(PID_NAME, PID_DIR).get_path(), in_developer_mode=in_developer_mode)

    if 'foreground' == command:
        # Run in the standard foreground.
        agent.start()

    elif 'info' == command:
        return Agent.info(verbose=options.verbose)

    elif 'check' == command:
        if len(args) < 2:
            sys.stderr.write(
                "Usage: %s check <check_name> [check_rate]\n"
                "Add check_rate as last argument to compute rates\n"
                % sys.argv[0]
            )
            return 1

        check_name = args[1]
        try:
            import checks.collector
            # Try the old-style check first
            print getattr(checks.collector, check_name)(log).check(agentConfig)
        except Exception:
            # If not an old-style check, try checks.d
            checks = load_check_directory(agentConfig, hostname)
            for check in checks['initialized_checks']:
                if check.name == check_name:
                    if in_developer_mode:
                        check.run = AgentProfiler.wrap_profiling(check.run)

                    cs = Collector.run_single_check(check, verbose=True)
                    print CollectorStatus.render_check_status(cs)

                    if len(args) == 3 and args[2] == 'check_rate':
                        print "Running 2nd iteration to capture rate metrics"
                        time.sleep(1)
                        cs = Collector.run_single_check(check, verbose=True)
                        print CollectorStatus.render_check_status(cs)

                    check.stop()

    elif 'configcheck' == command or 'configtest' == command:
        configcheck()
        sd_configcheck(agentConfig)

    elif 'jmx' == command:
        jmx_command(args[1:], agentConfig)

    elif 'flare' == command:
        Flare.check_user_rights()
        case_id = int(args[1]) if len(args) > 1 else None
        f = Flare(True, case_id)
        f.collect()
        try:
            f.upload()
        except Exception as e:
            print 'The upload failed:\n{0}'.format(str(e))

    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except StandardError:
        # Try our best to log the error.
        try:
            log.exception("Uncaught error running the Agent")
        except Exception:
            pass
        raise
