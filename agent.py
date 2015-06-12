#!/opt/datadog-agent/embedded/bin/python
'''
    Datadog
    www.datadoghq.com
    ----
    Make sense of your IT Data

    Licensed under Simplified BSD License (see LICENSE)
    (C) Boxed Ice 2010 all rights reserved
    (C) Datadog, Inc. 2010-2014 all rights reserved
'''
# set up logging before importing any other components
from config import get_version, initialize_logging # noqa
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
    get_confd_path,
    get_config,
    get_parsed_args,
    get_system_stats,
    load_check_directory,
)
from daemon import AgentSupervisor, Daemon
from emitter import http_emitter
from jmxfetch import JMX_LIST_COMMANDS, JMXFetch
from util import (
    EC2,
    get_hostname,
    get_os,
    Watchdog,
)
from utils.flare import configcheck, Flare
from utils.pidfile import PidFile
from utils.profile import AgentProfiler

# Constants
PID_NAME = "dd-agent"
WATCHDOG_MULTIPLIER = 10
RESTART_INTERVAL = 4 * 24 * 60 * 60  # Defaults to 4 days
START_COMMANDS = ['start', 'restart', 'foreground']
DD_AGENT_COMMANDS = ['check', 'flare', 'jmx']

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

    def _handle_sigterm(self, signum, frame):
        log.debug("Caught sigterm. Stopping run loop.")
        self.run_forever = False

        if self.collector:
            self.collector.stop()
        log.debug("Collector is stopped.")

    def _handle_sigusr1(self, signum, frame):
        self._handle_sigterm(signum, frame)
        self._do_restart()

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

        # Save the agent start-up stats.
        CollectorStatus().persist()

        # Intialize the collector.
        if not config:
            config = get_config(parse_args=True)

        agentConfig = self._set_agent_config_hostname(config)
        hostname = get_hostname(agentConfig)
        systemStats = get_system_stats()
        emitters = self._get_emitters(agentConfig)
        # Load the checks.d checks
        checksd = load_check_directory(agentConfig, hostname)

        self.collector = Collector(agentConfig, emitters, systemStats, hostname)

        # In developer mode, the number of runs to be included in a single collector profile
        collector_profile_interval = agentConfig.get('collector_profile_interval',
                                                     DEFAULT_COLLECTOR_PROFILE_INTERVAL)

        # Configure the watchdog.
        check_frequency = int(agentConfig['check_freq'])
        watchdog = self._get_watchdog(check_frequency, agentConfig)

        # Initialize the auto-restarter
        self.restart_interval = int(agentConfig.get('restart_interval', RESTART_INTERVAL))
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

            # Do the work.
            self.collector.run(checksd=checksd, start_event=self.start_event)
            if profiled:
                if collector_profiled_runs >= collector_profile_interval:
                    try:
                        profiler.disable_profiling()
                        profiled = False
                        collector_profiled_runs = 0
                    except Exception as e:
                        log.warn("Cannot disable profiler: %s" % str(e))

            # Check if we should restart.
            if self.autorestart and self._should_restart():
                self._do_restart()

            # Only plan for the next loop if we will continue,
            # otherwise just exit quickly.
            if self.run_forever:
                if watchdog:
                    watchdog.reset()
                if profiled:
                    collector_profiled_runs += 1
                time.sleep(check_frequency)
        # Now clean-up.
        try:
            CollectorStatus.remove_latest_status()
        except Exception:
            pass

        # Explicitly kill the process, because it might be running
        # as a daemon.
        log.info("Exiting. Bye bye.")
        sys.exit(0)

    def _get_emitters(self, agentConfig):
        return [http_emitter]

    def _get_watchdog(self, check_freq, agentConfig):
        watchdog = None
        if agentConfig.get("watchdog", True):
            watchdog = Watchdog(check_freq * WATCHDOG_MULTIPLIER,
                                max_mem_mb=agentConfig.get('limit_memory_consumption', None))
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

    # Deprecation notice
    if command not in DD_AGENT_COMMANDS:
        # Will become an error message and exit after deprecation period
        from utils.deprecations import deprecate_old_command_line_tools
        deprecate_old_command_line_tools()

    if command in COMMANDS_AGENT:
        agent = Agent(PidFile('dd-agent').get_path(), autorestart, in_developer_mode=in_developer_mode)

    if command in START_COMMANDS:
        log.info('Agent version %s' % get_version())

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
        logging.info('Running in foreground')
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

    elif 'jmx' == command:
        if len(args) < 2 or args[1] not in JMX_LIST_COMMANDS.keys():
            print "#" * 80
            print "JMX tool to be used to help configuring your JMX checks."
            print "See http://docs.datadoghq.com/integrations/java/ for more information"
            print "#" * 80
            print "\n"
            print "You have to specify one of the following commands:"
            for command, desc in JMX_LIST_COMMANDS.iteritems():
                print "      - %s [OPTIONAL: LIST OF CHECKS]: %s" % (command, desc)
            print "Example: sudo /etc/init.d/datadog-agent jmx list_matching_attributes tomcat jmx solr"
            print "\n"

        else:
            jmx_command = args[1]
            checks_list = args[2:]
            confd_directory = get_confd_path(get_os())

            jmx_process = JMXFetch(confd_directory, agentConfig)
            jmx_process.configure()
            should_run = jmx_process.should_run()

            if should_run:
                jmx_process.run(jmx_command, checks_list, reporter="console")
            else:
                print "Couldn't find any valid JMX configuration in your conf.d directory: %s" % confd_directory
                print "Have you enabled any JMX check ?"
                print "If you think it's not normal please get in touch with Datadog Support"

    elif 'flare' == command:
        Flare.check_user_rights()
        case_id = int(args[1]) if len(args) > 1 else None
        f = Flare(True, case_id)
        f.collect()
        try:
            f.upload()
        except Exception, e:
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
