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
from util import Watchdog, PidFile


# Constants
PID_NAME = "dd-agent"
WATCHDOG_MULTIPLIER = 10

# Globals
agent_logger = logging.getLogger('agent')


class Agent(Daemon):
    """
    The agent class is a daemon that runs the collector in a background process.
    """

    def __init__(self, pidfile):
        Daemon.__init__(self, pidfile)
        self.run_forever = True
        self.collector = None

    def _handle_sigterm(self, signum, frame):
        agent_logger.debug("Caught sigterm. Stopping run loop.")
        self.run_forever = False
        if self.collector:
            self.collector.stop()

    def run(self, config=None):
        """Main loop of the collector"""

        # Gracefully exit on sigterm.
        signal.signal(signal.SIGTERM, self._handle_sigterm)

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
       
        # Run the main loop.
        while self.run_forever:
            # Do the work.
            self.collector.run(checksd=checksd)

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
        agent_logger.info("Exiting. Bye bye.")
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
                agent_logger.info("Running on EC2, instanceId: %s" % instanceId)
                agentConfig['hostname'] = instanceId
            else:
                agent_logger.info('Not running on EC2, using hostname to identify this server')
        return agentConfig


def setup_logging(agentConfig):
    """Configure logging to use syslog whenever possible.
    Also controls debug_mode."""
    if agentConfig['debug_mode']:
        logFile = "/tmp/dd-agent.log"
        logging.basicConfig(filename=logFile, filemode='w',
        level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        logging.info("Logging to %s" % logFile)
    else:
        try:
            from logging.handlers import SysLogHandler
            rootLog = logging.getLogger()
            rootLog.setLevel(logging.INFO)

            sys_log_addr = "/dev/log"

            # Special-case macs
            if sys.platform == 'darwin':
                sys_log_addr = "/var/run/syslog"

            handler = SysLogHandler(address=sys_log_addr, facility=SysLogHandler.LOG_DAEMON)
            formatter = logging.Formatter("dd-agent - %(name)s - %(levelname)s - %(message)s")
            handler.setFormatter(formatter)
            rootLog.addHandler(handler)
            logging.info('Logging to syslog is set up')
        except Exception,e:
            sys.stderr.write("Error while setting up syslog logging (%s). No logging available" % str(e))
            logging.disable(logging.ERROR)


def main():
    options, args = get_parsed_args()
    agentConfig = get_config(options=options)

    # Logging
    setup_logging(agentConfig)


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

        agent = Agent(pid_file.get_path())

        if 'start' == command:
            logging.info('Start daemon')
            agent.start()

        elif 'stop' == command:
            logging.info('Stop daemon')
            agent.stop()

        elif 'restart' == command:
            logging.info('Restart daemon')
            agent.restart()

        elif 'foreground' == command:
            logging.info('Running in foreground')
            agent.run(config=agentConfig)

    # Commands that don't need the agent to be initialized.
    else:
        if 'status' == command:
            pid = pid_file.get_pid()
            if pid is not None:
                sys.stdout.write('dd-agent is running as pid %s.\n' % pid)
            else:
                sys.stdout.write('dd-agent is not running.\n')

        elif 'info' == command:
            return CollectorStatus.print_latest_status(verbose=options.verbose)

    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception:
        # Try our best to log the error.
        try:
            agent_logger.exception("Uncaught error running the agent")
        except:
            pass
        raise
