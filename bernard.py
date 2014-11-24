#!/usr/bin/env python

# set up logging before importing any other components
from config import initialize_logging; initialize_logging('bernard')

import os; os.umask(022)

# Core modules
import logging
import os
import os.path
import signal
import sys
import time

# Check we're not using an old version of Python. We need 2.4 above because some modules (like subprocess)
# were only introduced in 2.4.
if int(sys.version_info[1]) <= 3:
    sys.stderr.write("Datadog agent requires python 2.4 or later.\n")
    sys.exit(2)

# Custom modules
from checks.check_status import BernardStatus
from config import get_config, get_parsed_args, load_bernard_checks, get_bernard_config
from daemon import Daemon, AgentSupervisor
from util import PidFile, StaticWatchdog
from scheduler import Scheduler

# Constants
RESTART_INTERVAL = 4 * 24 * 60 * 60 # Defaults to 4 days

# Globals
log = logging.getLogger('bernard')

class Bernard(Daemon):
    """
    The Bernard class is a daemon that runs the scheduler in a background process.
    """

    def __init__(self, pidfile, autorestart, start_event=True):
        """ Initialization of the Dameon """
        Daemon.__init__(self, pidfile)
        self.run_forever = True
        self.scheduler = None
        self.autorestart = autorestart
        self.start_event = start_event
        StaticWatchdog.reset()

    def _handle_sigterm(self, signum, frame):
        log.debug("Caught sigterm. Stopping run loop.")
        self.run_forever = False

    def _handle_sigusr1(self, signum, frame):
        self._handle_sigterm(signum, frame)
        self._do_restart()

    def info(self, verbose=None):
        logging.getLogger().setLevel(logging.ERROR)
        return BernardStatus.print_latest_status(verbose=verbose)

    def run(self):
        """Main loop of Bernard"""

        simulated_time = False

        # Gracefully exit on sigterm.
        signal.signal(signal.SIGTERM, self._handle_sigterm)

        # A SIGUSR1 signals an exit with an autorestart
        signal.signal(signal.SIGUSR1, self._handle_sigusr1)

        # Handle Keyboard Interrupt
        signal.signal(signal.SIGINT, self._handle_sigterm)

        # load Bernard config and checks
        bernard_config = get_bernard_config()
        bernard_checks = load_bernard_checks(bernard_config)

        # Exit Bernard if there is no check
        if not bernard_checks:
            log.info("No checks found, exiting.")
            time.sleep(3)
            sys.exit(0)

        # Save the agent start-up stats.
        BernardStatus(checks=bernard_checks).persist()
        self.last_info_update = time.time()

        # Initialize the auto-restarter
        self.restart_interval = int(RESTART_INTERVAL)
        self.agent_start = time.time()

        # Initialize the Scheduler
        self.scheduler = Scheduler(checks=bernard_checks, config=bernard_config,
            simulated_time=simulated_time)

        # Run the main loop.
        while self.run_forever:
            # Run the next scheduled check
            self.scheduler.process()

            wait_time = self.scheduler.wait_time()

            # Check if we should restart.
            if self.autorestart and self._should_restart():
                self._do_restart()

            # Update status only if more than 10s or before a long sleep
            if time.time() > self.last_info_update + 10 or wait_time > 10:
                BernardStatus(checks=self.scheduler.checks,
                    schedule_count=self.scheduler.schedule_count).persist()
                self.last_info_update = time.time()

            # Only plan for the next loop if we will continue,
            # otherwise just exit quickly.
            if self.run_forever:
                # Give more time to the Watchdog because of the sleep
                StaticWatchdog.reset(int(wait_time))
                # Sleep until the next task schedule
                time.sleep(self.scheduler.wait_time())

        # Now clean-up.
        BernardStatus.remove_latest_status()

        # Explicitly kill the process, because it might be running
        # as a daemon.
        log.info("Exiting. Bye bye.")
        sys.exit(0)

    def _should_restart(self):
        if time.time() - self.agent_start > self.restart_interval:
            return True
        return False

    def _do_restart(self):
        log.info("Running an auto-restart.")
        sys.exit(AgentSupervisor.RESTART_EXIT_STATUS)

def main():
    """" Execution of Bernard"""
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
    ]

    if len(args) < 1:
        sys.stderr.write("Usage: %s %s\n" % (sys.argv[0], "|".join(COMMANDS)))
        return 2

    command = args[0]
    if command not in COMMANDS:
        sys.stderr.write("Unknown command: %s\n" % command)
        return 3

    pid_file = PidFile('bernard')

    if options.clean:
        pid_file.clean()

    bernard = Bernard(pid_file.get_path(), autorestart)

    if 'start' == command:
        log.info('Start daemon')
        bernard.start()

    elif 'stop' == command:
        log.info('Stop daemon')
        bernard.stop()

    elif 'restart' == command:
        log.info('Restart daemon')
        bernard.restart()

    elif 'status' == command:
        bernard.status()

    elif 'info' == command:
        bernard.info(verbose=options.verbose)

    elif 'foreground' == command:
        logging.info('Running in foreground')
        if autorestart:
            # Set-up the supervisor callbacks and fork it.
            logging.info('Running Bernard with auto-restart ON')
            def child_func(): bernard.run()
            def parent_func(): bernard.start_event = False
            AgentSupervisor.start(parent_func, child_func)
        else:
            # Run in the standard foreground.
            bernard.run()

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

