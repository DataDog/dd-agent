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

# Core modules
import logging
import modules
import os
import os.path
import re
import sys
import time
import urllib

# Constants
PID_NAME="dd-agent"

WATCHDOG_MULTIPLIER = 10 # will fire if no checks have been collected in N * check_freq, 150s by default

# Check we're not using an old version of Python. We need 2.4 above because some modules (like subprocess)
# were only introduced in 2.4.
if int(sys.version_info[1]) <= 3:
    sys.stderr.write("Datadog agent requires python 2.4 or later.\n")
    sys.exit(2)

# Custom modules
from checks.collector import Collector
from checks.ec2 import EC2
from config import get_config, get_system_stats, get_parsed_args, load_check_directory
from daemon import Daemon
from emitter import http_emitter
from util import Watchdog, PidFile


class Agent(Daemon):
    """
    The agent class is a daemon that runs the agent in a background process.
    """

    def run(self, agentConfig=None, run_forever=True):
        """Main loop of the collector"""
        agentLogger = logging.getLogger('agent')
        systemStats = get_system_stats()

        if agentConfig is None:
            agentConfig = get_config()

        # Load the checks.d checks
        checksd = load_check_directory(agentConfig)

        # Try to fetch instance Id from EC2 if not hostname has been set
        # in the config file.
        # DEPRECATED
        if agentConfig.get('hostname') is None and agentConfig.get('use_ec2_instance_id'):
            instanceId = EC2.get_instance_id()
            if instanceId is not None:
                agentLogger.info("Running on EC2, instanceId: %s" % instanceId)
                agentConfig['hostname'] = instanceId
            else:
                agentLogger.info('Not running on EC2, using hostname to identify this server')

        emitters = [http_emitter]

        check_freq = int(agentConfig['check_freq'])

        # Checks instance
        collector = Collector(agentConfig, emitters, systemStats)

        # Watchdog
        watchdog = None
        if agentConfig.get("watchdog", True):
            watchdog = Watchdog(check_freq * WATCHDOG_MULTIPLIER)
            watchdog.reset()

        # Main loop
        while run_forever:
            collector.run(checksd=checksd)
            if watchdog is not None:
                watchdog.reset()
            time.sleep(check_freq)

def setupLogging(agentConfig):
    """Configure logging to use syslog whenever possible.
    Also controls debug_mode."""
    if agentConfig['debug_mode']:
        logFile = "/tmp/dd-agent.log"
        logging.basicConfig(filename=logFile, filemode='w', level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
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


# Control of daemon
if __name__ == '__main__':
    options, args = get_parsed_args()
    agentConfig = get_config()

    # Logging
    setupLogging(agentConfig)

    if len(args) > 0:
        command = args[0]

        pid_file = PidFile('dd-agent')

        if options.clean:
            pid_file.clean()

        daemon = Agent(pid_file.get_path())

        if 'start' == command:
            logging.info('Start daemon')
            daemon.start()

        elif 'stop' == command:
            logging.info('Stop daemon')
            daemon.stop()

        elif 'restart' == command:
            logging.info('Restart daemon')
            daemon.restart()

        elif 'foreground' == command:
            logging.info('Running in foreground')
            daemon.run()

        elif 'status' == command:
            pid = pid_file.get_pid()
            if pid is not None:
                sys.stdout.write('dd-agent is running as pid %s.\n' % pid)
                logging.info("dd-agent is running as pid %s." % pid)
            else:
                sys.stdout.write('dd-agent is not running.\n')
                logging.info("dd-agent is not running.")

        else:
            sys.stderr.write('Unknown command: %s.\n' % sys.argv[1])
            sys.exit(2)

        sys.exit(0)

    else:
        sys.stderr.write('Usage: %s start|stop|restart|foreground|status' % sys.argv[0])
        sys.exit(2)
