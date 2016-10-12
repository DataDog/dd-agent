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
import supervisor.xmlrpc
import xmlrpclib
from copy import copy

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
    load_check,
    generate_jmx_configs
)
from daemon import AgentSupervisor, Daemon
from emitter import http_emitter
from utils.platform import Platform

# utils
from util import Watchdog
from utils.cloud_metadata import EC2
from utils.configcheck import configcheck, sd_configcheck
from utils.flare import Flare
from utils.hostname import get_hostname
from utils.jmx import jmx_command
from utils.pidfile import PidFile
from utils.profile import AgentProfiler
from utils.service_discovery.config_stores import get_config_store
from utils.service_discovery.sd_backend import get_sd_backend

# Constants
from jmxfetch import JMX_CHECKS
PID_NAME = "dd-agent"
PID_DIR = None
WATCHDOG_MULTIPLIER = 10
RESTART_INTERVAL = 4 * 24 * 60 * 60  # Defaults to 4 days

JMX_SUPERVISOR_ENTRY = 'datadog-agent:jmxfetch'
JMX_GRACE_SECS = 2
SERVICE_DISCOVERY_PREFIX = 'SD-'
SD_PIPE_NAME = "dd-service_discovery"
SD_PIPE_UNIX_PATH = "/tmp"
SD_PIPE_WIN_PATH = "\\\\.\\pipe\\{pipename}"
SD_CONFIG_SEP = "#### SERVICE-DISCOVERY ####\n"

DEFAULT_SUPERVISOR_SOCKET = '/opt/datadog-agent/run/datadog-supervisor.sock'
DEFAULT_COLLECTOR_PROFILE_INTERVAL = 20

# Globals
log = logging.getLogger('collector')


class Agent(Daemon):
    """
    The agent class is a daemon that runs the collector in a background process.
    """

    def __init__(self, pidfile, autorestart, start_event=True, in_developer_mode=False):
        Daemon.__init__(self, pidfile, autorestart=autorestart)
        self.run_forever = True
        self.collector = None
        self.start_event = start_event
        self.in_developer_mode = in_developer_mode
        self._agentConfig = {}
        self._checksd = []
        self.collector_profile_interval = DEFAULT_COLLECTOR_PROFILE_INTERVAL
        self.check_frequency = None
        # this flag can be set to True, False, or a list of checks (for partial reload)
        self.reload_configs_flag = False
        self.sd_backend = None
        self.supervisor_proxy = None

        if Platform.is_windows():
            pipe_name = SD_PIPE_WIN_PATH.format(pipename=SD_PIPE_NAME)
        else:
            pipe_name = os.path.join(SD_PIPE_UNIX_PATH, SD_PIPE_NAME)

        if not os.path.exists(pipe_name):
            os.mkfifo(pipe_name)
        self.sd_pipe = os.open(pipe_name, os.O_RDWR) # RW to avoid blocking (will only W)

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

    def reload_configs(self, checks_to_reload=set()):
        """Reload the agent configuration and checksd configurations.
           Can also reload only an explicit set of checks."""
        log.info("Attempting a configuration reload...")
        hostname = get_hostname(self._agentConfig)

        # if no check was given, reload them all
        if not checks_to_reload:
            log.debug("No check list was passed, reloading every check")
            # stop checks
            for check in self._checksd.get('initialized_checks', []):
                check.stop()

            self._checksd = load_check_directory(self._agentConfig, hostname)
            jmx_sd_configs = generate_jmx_configs(self._agentConfig, hostname)
        else:
            new_checksd = copy(self._checksd)

            jmx_checks = [check for check in checks_to_reload if check in JMX_CHECKS]
            py_checks = set(checks_to_reload) - set(jmx_checks)
            self.refresh_specific_checks(hostname, new_checksd, py_checks)
            jmx_sd_configs = generate_jmx_configs(self._agentConfig, hostname, jmx_checks)

            # once the reload is done, replace existing checks with the new ones
            self._checksd = new_checksd

        if jmx_sd_configs:
            self._submit_jmx_service_discovery(jmx_sd_configs)

        # Logging
        num_checks = len(self._checksd['initialized_checks'])
        if num_checks > 0:
            opt_msg = " (refreshed %s checks)" % len(checks_to_reload) if checks_to_reload else ''

            msg = "Check reload was successful. Running {num_checks} checks{opt_msg}.".format(
                num_checks=num_checks, opt_msg=opt_msg)
            log.info(msg)
        else:
            log.info("No checksd configs found")

    def refresh_specific_checks(self, hostname, checksd, checks):
        """take a list of checks and for each of them:
            - remove it from the init_failed_checks if it was there
            - load a fresh config for it
            - replace its old config with the new one in initialized_checks if there was one
            - disable the check if no new config was found
            - otherwise, append it to initialized_checks
        """
        for check_name in checks:
            idx = None
            for num, check in enumerate(checksd['initialized_checks']):
                if check.name == check_name:
                    idx = num
                    # stop the existing check before reloading it
                    check.stop()

            if not idx and check_name in checksd['init_failed_checks']:
                # if the check previously failed to load, pop it from init_failed_checks
                checksd['init_failed_checks'].pop(check_name)

            fresh_check = load_check(self._agentConfig, hostname, check_name)

            # this is an error dict
            # checks that failed to load are added to init_failed_checks
            # and poped from initialized_checks
            if isinstance(fresh_check, dict) and 'error' in fresh_check.keys():
                checksd['init_failed_checks'][fresh_check.keys()[0]] = fresh_check.values()[0]
                if idx:
                    checksd['initialized_checks'].pop(idx)

            elif not fresh_check:
                # no instance left of it to monitor so the check was not loaded
                if idx:
                    checksd['initialized_checks'].pop(idx)
                # the check was not previously running so we were trying to instantiate it and it failed
                else:
                    log.error("Configuration for check %s was not found, it won't be reloaded." % check_name)

            # successfully reloaded check are added to initialized_checks
            # (appended or replacing a previous version)
            else:
                if idx is not None:
                    checksd['initialized_checks'][idx] = fresh_check
                # it didn't exist before and doesn't need to be replaced so we append it
                else:
                    checksd['initialized_checks'].append(fresh_check)

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

        # Initialize Supervisor proxy (unix specific)
        self.supervisor_proxy = self._get_supervisor_socket(self._agentConfig)

        # Load the checks.d checks
        self._checksd = load_check_directory(self._agentConfig, hostname)

        # Load JMX configs if available
        jmx_sd_configs = generate_jmx_configs(self._agentConfig, hostname)
        if jmx_sd_configs:
            self._submit_jmx_service_discovery(jmx_sd_configs)

        # Initialize the Collector
        self.collector = Collector(self._agentConfig, emitters, systemStats, hostname)

        # In developer mode, the number of runs to be included in a single collector profile
        try:
            self.collector_profile_interval = int(
                self._agentConfig.get('collector_profile_interval', DEFAULT_COLLECTOR_PROFILE_INTERVAL))
        except ValueError:
            log.warn('collector_profile_interval is invalid. '
                     'Using default value instead (%s).' % DEFAULT_COLLECTOR_PROFILE_INTERVAL)
            self.collector_profile_interval = DEFAULT_COLLECTOR_PROFILE_INTERVAL

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
                if isinstance(self.reload_configs_flag, set):
                    self.reload_configs(checks_to_reload=self.reload_configs_flag)
                else:
                    self.reload_configs()

            # Do the work. Pass `configs_reloaded` to let the collector know if it needs to
            # look for the AgentMetrics check and pop it out.
            self.collector.run(checksd=self._checksd,
                               start_event=self.start_event,
                               configs_reloaded=True if self.reload_configs_flag else False)

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
                self.reload_configs_flag = self.sd_backend.reload_check_configs
                self.sd_backend.reload_check_configs = False

            if profiled:
                if collector_profiled_runs >= self.collector_profile_interval:
                    try:
                        profiler.disable_profiling()
                        profiled = False
                        collector_profiled_runs = 0
                    except Exception as e:
                        log.warn("Cannot disable profiler: %s" % str(e))

            # Check if we should restart.
            if self.autorestart and self._should_restart():
                self._do_restart()

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

        # Explicitly kill the process, because it might be running as a daemon.
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

    def _get_supervisor_socket(self, agentConfig):
        if Platform.is_windows():
            return None

        sockfile = agentConfig.get('supervisor_socket', DEFAULT_SUPERVISOR_SOCKET)
        supervisor_proxy = xmlrpclib.ServerProxy(
            'http://127.0.0.1',
            transport=supervisor.xmlrpc.SupervisorTransport(
                None, None, serverurl="unix://{socket}".format(socket=sockfile))
        )

        return supervisor_proxy

    def _submit_jmx_service_discovery(self, jmx_sd_configs):

        if not jmx_sd_configs:
            return

        if self.supervisor_proxy is not None:
            jmx_state = self.supervisor_proxy.supervisor.getProcessInfo(JMX_SUPERVISOR_ENTRY)
            log.debug("Current JMX check state: %s", jmx_state['statename'])
            # restart jmx if stopped
            if jmx_state['statename'] in ['STOPPED', 'EXITED', 'FATAL'] and self._agentConfig.get('sd_jmx_enable'):
                self.supervisor_proxy.supervisor.startProcess(JMX_SUPERVISOR_ENTRY)
                time.sleep(JMX_GRACE_SECS)
        else:
            log.debug("Unable to automatically start jmxfetch on Windows via supervisor.")

        buffer = ""
        for name, yaml in jmx_sd_configs.iteritems():
            try:
                buffer += SD_CONFIG_SEP
                buffer += "# {}\n".format(name)
                buffer += yaml
            except Exception as e:
                log.exception("unable to submit YAML via RPC: %s", e)
            else:
                log.info("JMX SD Config via named pip %s successfully.", name)

        if buffer:
            os.write(self.sd_pipe, buffer)

    def _should_restart(self):
        if time.time() - self.agent_start > self.restart_interval:
            return True
        return False

    def _do_restart(self):
        log.info("Running an auto-restart.")
        if self.collector:
            self.collector.stop()
        sys.exit(AgentSupervisor.RESTART_EXIT_STATUS)


def main():
    options, args = get_parsed_args()
    agentConfig = get_config(options=options)
    autorestart = agentConfig.get('autorestart', False)
    hostname = get_hostname(agentConfig)
    in_developer_mode = agentConfig.get('developer_mode')

    COMMANDS_AGENT = [
        'start',
        'stop',
        'restart',
        'status',
        'foreground',
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
    if command not in COMMANDS:
        sys.stderr.write("Unknown command: %s\n" % command)
        return 3

    # TODO: actually kill the start/stop/restart/status command for 5.11
    if command in ['start', 'stop', 'restart', 'status'] and not in_developer_mode:
        logging.error('Please use supervisor to manage the agent')
        return 1

    if command in COMMANDS_AGENT:
        agent = Agent(PidFile(PID_NAME, PID_DIR).get_path(), autorestart, in_developer_mode=in_developer_mode)

    if 'start' == command:
        log.info('Start daemon')
        agent.start()

    elif 'stop' == command:
        log.info('Stop daemon')
        agent.stop()

    elif 'restart' == command:
        log.info('Restart daemon')
        agent.restart()

    elif 'status' == command:
        agent.status()

    elif 'info' == command:
        return Agent.info(verbose=options.verbose)

    elif 'foreground' == command:
        log.info('Agent version %s' % get_version())
        if autorestart:
            # Set-up the supervisor callbacks and fork it.
            logging.info('Running Agent with auto-restart ON')

            def child_func():
                agent.start(foreground=True)

            def parent_func():
                agent.start_event = False

            AgentSupervisor.start(parent_func, child_func)
        else:
            # Run in the standard foreground.
            agent.start(foreground=True)

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
