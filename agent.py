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
from config import get_version, initialize_logging; initialize_logging('collector')

import os; os.umask(022)

# Core modules
import logging
import os.path
import signal
import sys
import time
import glob
import tarfile
import subprocess
import json
import tempfile
import re
import atexit

# Custom modules
from checks.collector import Collector
from checks.check_status import CollectorStatus, DogstatsdStatus, ForwarderStatus
from config import get_config, get_system_stats, get_parsed_args,\
                   load_check_directory, get_logging_config, check_yaml,\
                   get_config, get_config_path, get_confd_path
from daemon import Daemon, AgentSupervisor
from emitter import http_emitter
from util import Watchdog, PidFile, EC2, get_os, get_hostname
from jmxfetch import JMXFetch

# 3p
import requests

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
        hostname = get_hostname(agentConfig)
        systemStats = get_system_stats()
        emitters = self._get_emitters(agentConfig)
        # Load the checks.d checks
        checksd = load_check_directory(agentConfig, hostname)

        self.collector = Collector(agentConfig, emitters, systemStats, hostname)

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

def configcheck():
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

class Flare(object):
    """
    Compress all important logs and configuration files for debug,
    and then send them to Datadog (which transfers them to Support)
    """

    DATADOG_SUPPORT_URL = '/zendesk/flare'
    PASSWORD_REGEX = re.compile('( *(\w|_)*pass(word)?:).+')
    COMMENT_REGEX = re.compile('^ *#.*')
    APIKEY_REGEX = re.compile('^api_key:')

    def __init__(self, cmdline=False, case_id=None):
        self._case_id = case_id
        self._cmdline = cmdline
        self._init_tarfile()
        self._save_logs_path(get_logging_config())
        config = get_config()
        self._api_key = config.get('api_key')
        self._url = "{0}{1}".format(config.get('dd_url'), self.DATADOG_SUPPORT_URL)
        self._hostname = get_hostname(config)
        self._prefix = "datadog-{0}".format(self._hostname)

    def collect(self):
        if not self._api_key:
            raise Exception('No api_key found')
        self._print("Collecting logs and configuration files:")

        self._add_logs_tar()
        self._add_conf_tar()
        self._print("  * datadog-agent configcheck output")
        self._add_command_output_tar('configcheck.log', configcheck)
        self._print("  * datadog-agent status output")
        self._add_command_output_tar('status.log', self._supervisor_status)
        self._print("  * datadog-agent info output")
        self._add_command_output_tar('info.log', self._info_all)

        self._print("Saving all files to {0}".format(self._tar_path))
        self._tar.close()

    # Upload the tar file
    def upload(self, confirmation=True):
        # Ask for confirmation first
        if confirmation:
            self._ask_for_confirmation()

        email = self._ask_for_email()

        self._print("Uploading {0} to Datadog Support".format(self._tar_path))
        url = self._url
        if self._case_id:
            url = "{0}/{1}".format(self._url, str(self._case_id))
        files = {'flare_file': open(self._tar_path, 'rb')}
        data = {
            'api_key': self._api_key,
            'case_id': self._case_id,
            'hostname': self._hostname,
            'email': email
        }
        r = requests.post(url, files=files, data=data)
        self._analyse_result(r)

    # Start by creating the tar file which will contain everything
    def _init_tarfile(self):
        # Default temp path
        self._tar_path = os.path.join(tempfile.gettempdir(), 'datadog-agent.tar.bz2')

        if os.path.exists(self._tar_path):
            os.remove(self._tar_path)
        self._tar = tarfile.open(self._tar_path, 'w:bz2')

    # Save logs file paths
    def _save_logs_path(self, config):
        prefix = ''
        if get_os() == 'windows':
            prefix = 'windows_'
        self._collector_log = config.get('{0}collector_log_file'.format(prefix))
        self._forwarder_log = config.get('{0}forwarder_log_file'.format(prefix))
        self._dogstatsd_log = config.get('{0}dogstatsd_log_file'.format(prefix))
        self._jmxfetch_log = config.get('jmxfetch_log_file')

    # Add logs to the tarfile
    def _add_logs_tar(self):
        self._add_log_file_tar(self._collector_log)
        self._add_log_file_tar(self._forwarder_log)
        self._add_log_file_tar(self._dogstatsd_log)
        self._add_log_file_tar(self._jmxfetch_log)
        self._add_log_file_tar(
            "{0}/*supervisord.log*".format(os.path.dirname(self._collector_log))
        )

    def _add_log_file_tar(self, file_path):
        for f in glob.glob('{0}*'.format(file_path)):
            self._print("  * {0}".format(f))
            self._tar.add(
                f,
                os.path.join(self._prefix, 'log', os.path.basename(f))
            )

    # Collect all conf
    def _add_conf_tar(self):
        conf_path = get_config_path()
        self._print("  * {0}".format(conf_path))
        self._tar.add(
            self._strip_comment(conf_path),
            os.path.join(self._prefix, 'etc', 'datadog.conf')
        )

        if get_os() != 'windows':
            supervisor_path = os.path.join(
                os.path.dirname(get_config_path()),
                'supervisor.conf'
            )
            self._print("  * {0}".format(supervisor_path))
            self._tar.add(
                self._strip_comment(supervisor_path),
                os.path.join(self._prefix, 'etc', 'supervisor.conf')
            )

        for file_path in glob.glob(os.path.join(get_confd_path(), '*.yaml')):
            self._add_clean_confd(file_path)

    # Return path to a temp file without comment
    def _strip_comment(self, file_path):
        _, temp_path = tempfile.mkstemp(prefix='dd')
        atexit.register(os.remove, temp_path)
        temp_file = open(temp_path, 'w')
        orig_file = open(file_path, 'r').read()

        for line in orig_file.splitlines(True):
            if not self.COMMENT_REGEX.match(line) and not self.APIKEY_REGEX.match(line):
                temp_file.write(line)
        temp_file.close()

        return temp_path

    # Remove password before collecting the file
    def _add_clean_confd(self, file_path):
        basename = os.path.basename(file_path)

        temp_path, password_found = self._strip_password(file_path)
        self._print("  * {0}{1}".format(file_path, password_found))
        self._tar.add(
            temp_path,
            os.path.join(self._prefix, 'etc', 'conf.d', basename)
        )

    # Return path to a temp file without password and comment
    def _strip_password(self, file_path):
        _, temp_path = tempfile.mkstemp(prefix='dd')
        atexit.register(os.remove, temp_path)
        temp_file = open(temp_path, 'w')
        orig_file = open(file_path, 'r').read()
        password_found = ''
        for line in orig_file.splitlines(True):
            if self.PASSWORD_REGEX.match(line):
                line = re.sub(self.PASSWORD_REGEX, r'\1 ********', line)
                password_found = ' - this file contains a password which '\
                                 'has been removed in the version collected'
            if not self.COMMENT_REGEX.match(line):
                temp_file.write(line)
        temp_file.close()

        return temp_path, password_found

    # Add output of the command to the tarfile
    def _add_command_output_tar(self, name, command):
        temp_file = os.path.join(tempfile.gettempdir(), name)
        if os.path.exists(temp_file):
            os.remove(temp_file)
        backup = sys.stdout
        sys.stdout = open(temp_file, 'w')
        command()
        sys.stdout.close()
        sys.stdout = backup
        self._tar.add(temp_file, os.path.join(self._prefix, name))
        os.remove(temp_file)

    # Print supervisor status (and nothing on windows)
    def _supervisor_status(self):
        if get_os == 'windows':
            print 'Windows - status not implemented'
        else:
            print '/etc/init.d/datadog-agent status'
            self._print_output_command(['/etc/init.d/datadog-agent', 'status'])
            print 'supervisorctl status'
            self._print_output_command(['/opt/datadog-agent/bin/supervisorctl',
                                        '-c', '/etc/dd-agent/supervisor.conf',
                                        'status'])

    # Print output of command
    def _print_output_command(self, command):
        try:
            status = subprocess.check_output(command, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError, e:
            status = 'Not able to get status, exit number {0}, exit ouput:\n'\
                     '{1}'.format(str(e.returncode), e.output)
        print status

    # Print info of all agent components
    def _info_all(self):
        CollectorStatus.print_latest_status(verbose=True)
        DogstatsdStatus.print_latest_status(verbose=True)
        ForwarderStatus.print_latest_status(verbose=True)

    # Function to ask for confirmation before upload
    def _ask_for_confirmation(self):
        print '{0} is going to be uploaded to Datadog.'.format(self._tar_path)
        print 'Do you want to continue [Y/n]?',
        choice = raw_input().lower()
        if choice not in ['yes', 'y', '']:
            print 'Aborting... (you can still use {0})'.format(self._tar_path)
            sys.exit(1)

    # Ask for email if needed
    def _ask_for_email(self):
        if self._case_id:
            return None
        print 'Please enter your email:',
        return raw_input().lower()

    # Print output (success/error) of the request
    def _analyse_result(self, resp):
        if resp.status_code == 200:
            self._print("Your logs were successfully uploaded. For future reference,"\
                        " your internal case id is {0}".format(json.loads(resp.text)['case_id']))
        elif resp.status_code == 400:
            raise Exception('Your request is incorrect, error {0}'.format(resp.text))
        elif resp.status_code == 500:
            raise Exception('An error has occurred while uploading: {0}'.format(resp.text))
        else:
            raise Exception('An unknown error has occured, please email support directly')

    # Print to the console or to the log
    def _print(self, output):
        if self._cmdline:
            print output
        else:
            log.info(output)

def main():
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
        'check',
        'configcheck',
        'jmx',
        'flare',
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
            def child_func(): agent.start(foreground=True)
            def parent_func(): agent.start_event = False
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
                    check.run()
                    print check.get_metrics()
                    print check.get_events()
                    print check.get_service_checks()
                    if len(args) == 3 and args[2] == 'check_rate':
                        print "Running 2nd iteration to capture rate metrics"
                        time.sleep(1)
                        check.run()
                        print check.get_metrics()
                        print check.get_events()
                        print check.get_service_checks()
                    check.stop()

    elif 'configcheck' == command or 'configtest' == command:
        configcheck()

    elif 'jmx' == command:
        from jmxfetch import JMX_LIST_COMMANDS, JMXFetch

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
            should_run = jmx_process.run(jmx_command, checks_list, reporter="console")
            if not should_run:
                print "Couldn't find any valid JMX configuration in your conf.d directory: %s" % confd_directory
                print "Have you enabled any JMX check ?"
                print "If you think it's not normal please get in touch with Datadog Support"

    elif 'flare' == command:
        case_id = int(args[1]) if len(args) > 1 else None
        f = Flare(True, case_id)
        f.collect()
        f.upload()

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
