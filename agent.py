#!/usr/bin/python
'''
    Datadog
    www.datadoghq.com
    ----
    Make sense of your IT Data

    Licensed under Simplified BSD License (see LICENSE)
    (C) Boxed Ice 2010 all rights reserved
    (C) Datadog, Inc. 2010 all rights reserved
'''

# set up logging before importing any other components
from config import initialize_logging; initialize_logging('collector')

import os; os.umask(022)

# Core modules
import logging
import modules
import os
import os.path
import re
import signal
import sys
import time
import urllib

# Check we're not using an old version of Python. We need 2.4 above because some modules (like subprocess)
# were only introduced in 2.4.
if int(sys.version_info[1]) <= 3:
    sys.stderr.write("Datadog agent requires python 2.4 or later.\n")
    sys.exit(2)

# Custom modules
from checks.collector import Collector
from checks.check_status import CollectorStatus
from checks.ec2 import EC2
from config import get_config, get_system_stats, get_parsed_args, load_check_directory
from daemon import Daemon
from emitter import http_emitter
from util import Watchdog, PidFile, AgentSupervisor


# Constants
PID_NAME = "dd-agent"
WATCHDOG_MULTIPLIER = 10
RESTART_INTERVAL = 4 * 24 * 60 * 60 # Defaults to 4 days

# Globals
log = logging.getLogger('collector')

class Agent(Daemon):
    """
    The agent class is a daemon that runs the collector in a background process.
    """

    def __init__(self, pidfile, autorestart, start_event=True):
        Daemon.__init__(self, pidfile)
        self.run_forever = True
        self.collector = None
        self.autorestart = autorestart
        self.start_event = start_event

    def _handle_sigterm(self, signum, frame):
        log.debug("Caught sigterm. Stopping run loop.")
        self.run_forever = False
        if self.collector:
            self.collector.stop()

    def _handle_sigusr1(self, signum, frame):
        self._handle_sigterm(signum, frame)
        self._do_restart()

    def run(self, config=None):
        """Main loop of the collector"""

        # Gracefully exit on sigterm.
        signal.signal(signal.SIGTERM, self._handle_sigterm)

        # A SIGUSR1 signals an exit with an autorestart
        signal.signal(signal.SIGUSR1, self._handle_sigusr1)

        # Save the agent start-up stats.
        CollectorStatus().persist()

        # Intialize the collector.
        if not config:
            config = get_config(parse_args=True)

        agentConfig = self._set_agent_config_hostname(config)
        systemStats = get_system_stats()
        emitters = self._get_emitters(agentConfig)
        self.collector = Collector(agentConfig, emitters, systemStats)

        # Load the checks.d checks
        checksd = load_check_directory(agentConfig)

        # Configure the watchdog.
        check_frequency = int(agentConfig['check_freq'])
        watchdog = self._get_watchdog(check_frequency, agentConfig)

        # Initialize the auto-restarter
        self.restart_interval = int(agentConfig.get('restart_interval', RESTART_INTERVAL))
        self.agent_start = time.time()

        # Run the main loop.
        while self.run_forever:
            # Do the work.
            self.collector.run(checksd=checksd, start_event=self.start_event)

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
        except:
            pass

        # Explicitly kill the process, because it might be running
        # as a daemon.
        log.info("Exiting. Bye bye.")
        sys.exit(0)

    def _get_emitters(self, agentConfig):
        emitters = [http_emitter]
        for emitter_spec in [s.strip() for s in agentConfig.get('custom_emitters', '').split(',')]:
            if len(emitter_spec) == 0: continue
            emitters.append(modules.load(emitter_spec, 'emitter'))
        return emitters

    def _get_watchdog(self, check_freq, agentConfig):
        watchdog = None
        if agentConfig.get("watchdog", True):
            watchdog = Watchdog(check_freq * WATCHDOG_MULTIPLIER)
            watchdog.reset()
        return watchdog

    def _set_agent_config_hostname(self, agentConfig):
        # Try to fetch instance Id from EC2 if not hostname has been set
        # in the config file.
        # DEPRECATED
        if agentConfig.get('hostname') is None and agentConfig.get('use_ec2_instance_id'):
            instanceId = EC2.get_instance_id()
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
        agent_logger.info("Running an auto-restart.")
        sys.exit(AgentSupervisor.RESTART_EXIT_STATUS)

def main():
    options, args = get_parsed_args()
    agentConfig = get_config(options=options)

    COMMANDS = [
        'start',
        'stop',
        'restart',
        'foreground',
        'status',
        'info',
    ]

    if len(args) < 1:
        sys.stderr.write("Usage: %s %s\n" % (sys.argv[0], "|".join(COMMANDS)))
        return 2

    command = args[0]
    if command not in COMMANDS:
        sys.stderr.write("Unknown command: %s\n" % command)
        return 3

    pid_file = PidFile('dd-agent')

    # Only initialize the Agent if we're starting or stopping it.
    if command in ['start', 'stop', 'restart', 'foreground']:

        if options.clean:
            pid_file.clean()

        agent = Agent(pid_file.get_path(), options.autorestart)

        if 'start' == command:
            log.info('Start daemon')
            agent.start()

        elif 'stop' == command:
            log.info('Stop daemon')
            agent.stop()

        elif 'restart' == command:
            log.info('Restart daemon')
            agent.restart()

        elif 'foreground' == command:
            logging.info('Running in foreground')

            if options.autorestart:
                # Set-up the supervisor callbacks and fork it.
                logging.info('Running Agent with auto-restart ON')
                def child_func(): agent.run()
                def parent_func(): agent.start_event = False
                AgentSupervisor.start(parent_func, child_func)
            else:
                # Run in the standard foreground.
                agent.run(config=agentConfig)

    # Commands that don't need the agent to be initialized.
    else:
        if 'status' == command:
            pid = pid_file.get_pid()
            if pid is not None:
                sys.stdout.write('dd-agent is running as pid %s.\n' % pid)
                log.info("dd-agent is running as pid %s." % pid)
            else:
                sys.stdout.write('dd-agent is not running.\n')
                log.info("dd-agent is not running.")

        elif 'info' == command:
            logging.getLogger().setLevel(logging.ERROR)
            return CollectorStatus.print_latest_status(verbose=options.verbose)

    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except StandardError:
        # Try our best to log the error.
        try:
            log.exception("Uncaught error running the agent")
        except:
            pass
        raise
