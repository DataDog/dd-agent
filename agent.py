#!/usr/bin/env python
'''
    Datadog
    www.datadoghq.com
    ----
    Make sense of your IT Data

    Licensed under Simplified BSD License (see LICENSE)
    (C) Boxed Ice 2010 all rights reserved
    (C) Datadog, Inc. 2010-2013 all rights reserved
'''

# set up logging before importing any other components
from config import get_version, initialize_logging; initialize_logging('collector')

import os; os.umask(022)

# Core modules
import logging
import os.path
import signal
import sys
import time
import glob

# Check we're not using an old version of Python. We need 2.4 above because some modules (like subprocess)
# were only introduced in 2.4.
if int(sys.version_info[1]) <= 3:
    sys.stderr.write("Datadog Agent requires python 2.4 or later.\n")
    sys.exit(2)

# Custom modules
from checks.collector import Collector
from checks.check_status import CollectorStatus
from config import get_config, get_system_stats, get_parsed_args, load_check_directory, get_confd_path, check_yaml, get_logging_config
from daemon import Daemon, AgentSupervisor
from emitter import http_emitter
from util import Watchdog, PidFile, EC2, get_os
from jmxfetch import JMXFetch


# Constants
PID_NAME = "dd-agent"
WATCHDOG_MULTIPLIER = 10
RESTART_INTERVAL = 4 * 24 * 60 * 60 # Defaults to 4 days
START_COMMANDS = ['start', 'restart', 'foreground']

# Globals
log = logging.getLogger('collector')

class Agent(Daemon):
    """
    The agent class is a daemon that runs the collector in a background process.
    """

    def __init__(self, pidfile, autorestart, start_event=True):
        Daemon.__init__(self, pidfile, autorestart=autorestart)
        self.run_forever = True
        self.collector = None
        self.start_event = start_event

    def _handle_sigterm(self, signum, frame):
        log.debug("Caught sigterm. Stopping run loop.")
        self.run_forever = False

        if JMXFetch.is_running():
            JMXFetch.stop()

        if self.collector:
            self.collector.stop()
        log.debug("Collector is stopped.")

    def _handle_sigusr1(self, signum, frame):
        self._handle_sigterm(signum, frame)
        self._do_restart()

    def info(self, verbose=None):
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
        systemStats = get_system_stats()
        emitters = self._get_emitters(agentConfig)
        # Load the checks.d checks
        checksd = load_check_directory(agentConfig)

        self.collector = Collector(agentConfig, emitters, systemStats)

        # Configure the watchdog.
        check_frequency = int(agentConfig['check_freq'])
        watchdog = self._get_watchdog(check_frequency, agentConfig)

        # Initialize the auto-restarter
        self.restart_interval = int(agentConfig.get('restart_interval', RESTART_INTERVAL))
        self.agent_start = time.time()

        # Run the main loop.
        while self.run_forever:
            
            # enable profiler if needed
            profiled = False
            if agentConfig.get('profile', False) and agentConfig.get('profile').lower() == 'yes':
                try:
                    import cProfile
                    profiler = cProfile.Profile()
                    profiled = True
                    profiler.enable()
                    log.debug("Agent profiling is enabled")
                except Exception:
                    log.warn("Cannot enable profiler")
                    
            # Do the work.
            self.collector.run(checksd=checksd, start_event=self.start_event)

            # disable profiler and printout stats to stdout
            if agentConfig.get('profile', False) and agentConfig.get('profile').lower() == 'yes' and profiled:
                try:
                    profiler.disable()
                    import pstats
                    from cStringIO import StringIO
                    s = StringIO()
                    ps = pstats.Stats(profiler, stream=s).sort_stats("cumulative")
                    ps.print_stats()
                    log.debug(s.getvalue())
                except Exception:
                    log.warn("Cannot disable profiler")

            # Check if we should restart.
            if self.autorestart and self._should_restart():
                self._do_restart()

            # Only plan for the next loop if we will continue,
            # otherwise just exit quickly.
            if self.run_forever:
                if watchdog:
                    watchdog.reset()
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

    COMMANDS = [
        'start',
        'stop',
        'restart',
        'foreground',
        'status',
        'info',
        'check',
        'configcheck',
        'jmx',
    ]

    if len(args) < 1:
        sys.stderr.write("Usage: %s %s\n" % (sys.argv[0], "|".join(COMMANDS)))
        return 2

    command = args[0]
    if command not in COMMANDS:
        sys.stderr.write("Unknown command: %s\n" % command)
        return 3

    pid_file = PidFile('dd-agent')

    if options.clean:
        pid_file.clean()

    agent = Agent(pid_file.get_path(), autorestart)

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
        return agent.info(verbose=options.verbose)

    elif 'foreground' == command:
        logging.info('Running in foreground')
        if autorestart:
            # Set-up the supervisor callbacks and fork it.
            logging.info('Running Agent with auto-restart ON')
            def child_func(): agent.run()
            def parent_func(): agent.start_event = False
            AgentSupervisor.start(parent_func, child_func)
        else:
            # Run in the standard foreground.
            agent.run(config=agentConfig)

    elif 'check' == command:
        check_name = args[1]
        try:
            import checks.collector
            # Try the old-style check first
            print getattr(checks.collector, check_name)(log).check(agentConfig)
        except Exception:
            # If not an old-style check, try checks.d
            checks = load_check_directory(agentConfig)
            for check in checks['initialized_checks']:
                if check.name == check_name:
                    check.run()
                    print check.get_metrics()
                    print check.get_events()
                    if len(args) == 3 and args[2] == 'check_rate':
                        print "Running 2nd iteration to capture rate metrics"
                        time.sleep(1)
                        check.run()
                        print check.get_metrics()
                        print check.get_events()

    elif 'configcheck' == command or 'configtest' == command:
        osname = get_os()
        all_valid = True
        for conf_path in glob.glob(os.path.join(get_confd_path(osname), "*.yaml")):
            basename = os.path.basename(conf_path)
            try:
                check_yaml(conf_path)
            except Exception, e:
                all_valid = False
                print "%s contains errors:\n    %s" % (basename, e)
            else:
                print "%s is valid" % basename
        if all_valid:
            print "All yaml files passed. You can now run the Datadog agent."
            return 0
        else:
            print("Fix the invalid yaml files above in order to start the Datadog agent. "
                    "A useful external tool for yaml parsing can be found at "
                    "http://yaml-online-parser.appspot.com/")
            return 1

    elif 'jmx' == command:
        from jmxfetch import JMX_LIST_COMMANDS, JMXFetch
       
        if len(args) < 2 or args[1] not in JMX_LIST_COMMANDS.keys():
            print "#" * 80
            print "JMX tool to be used to help configuring your JMX checks."
            print "See http://docs.datadoghq.com/integrations/java/ for more information"
            print "#" * 80
            print "\n"
            print "You have to specify one of the following command:" 
            for command, desc in JMX_LIST_COMMANDS.iteritems():
                print "      - %s [OPTIONAL: LIST OF CHECKS]: %s" % (command, desc)
            print "Example: sudo /etc/init.d/datadog-agent jmx list_matching_attributes tomcat jmx solr"
            print "\n"

        else:
            jmx_command = args[1]
            checks_list = args[2:]
            confd_directory = get_confd_path(get_os())
            should_run  = JMXFetch.init(confd_directory, agentConfig, get_logging_config(), 15, jmx_command, checks_list, reporter="console")
            if not should_run:
                print "Couldn't find any valid JMX configuration in your conf.d directory: %s" % confd_directory
                print "Have you enabled any JMX check ?"
                print "If you think it's not normal please get in touch with Datadog Support"


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
