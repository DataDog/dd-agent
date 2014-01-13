#!/usr/bin/env python

# stdlib
import logging
import sys

# project
from bernard.core import Bernard
from config import initialize_logging, get_config, get_parsed_args
from daemon import AgentSupervisor
from util import (
    PidFile,
    get_hostname,
)

log = logging.getLogger(__name__)

def main():
    """" Execution of Bernard"""
    # Check we're not using an old version of Python. We need 2.4 above because
    # some modules (like subprocess) were only introduced in 2.4.
    if int(sys.version_info[1]) <= 3:
        sys.stderr.write("Datadog agent requires python 2.4 or later.\n")
        sys.exit(2)

    initialize_logging('bernard')
    options, args = get_parsed_args()
    agentConfig = get_config(options=options)
    autorestart = agentConfig.get('autorestart', False)
    hostname = get_hostname(agentConfig)

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

    bernard = Bernard(pid_file.get_path(), hostname, autorestart)

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
        log.info('Running in foreground')
        if autorestart:
            # Set-up the supervisor callbacks and fork it.
            log.info('Running Bernard with auto-restart ON')
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
