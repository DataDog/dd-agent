# stdlib
import atexit
import cStringIO as StringIO
import glob
import logging
import os.path
import re
import subprocess
import sys
import tarfile
import tempfile
from time import strftime

# 3p
import requests

# DD imports
from checks.check_status import CollectorStatus, DogstatsdStatus, ForwarderStatus
from config import (
    check_yaml,
    get_confd_path,
    get_config,
    get_config_path,
    get_logging_config,
    get_url_endpoint,
)
from util import get_hostname
from utils.platform import Platform

# Globals
log = logging.getLogger(__name__)


def configcheck():
    all_valid = True
    for conf_path in glob.glob(os.path.join(get_confd_path(), "*.yaml")):
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

    DATADOG_SUPPORT_URL = '/support/flare'
    PASSWORD_REGEX = re.compile('( *(\w|_)*pass(word)?:).+')
    COMMENT_REGEX = re.compile('^ *#.*')
    APIKEY_REGEX = re.compile('^api_key: *\w+(\w{5})$')
    REPLACE_APIKEY = r'api_key: *************************\1'
    COMPRESSED_FILE = 'datadog-agent-{0}.tar.bz2'
    # We limit to 10MB arbitrarily
    MAX_UPLOAD_SIZE = 10485000
    TIMEOUT = 60

    def __init__(self, cmdline=False, case_id=None):
        self._case_id = case_id
        self._cmdline = cmdline
        self._init_tarfile()
        self._save_logs_path()
        config = get_config()
        self._api_key = config.get('api_key')
        self._url = "{0}{1}".format(
            get_url_endpoint(config.get('dd_url'), endpoint_type='flare'),
            self.DATADOG_SUPPORT_URL
        )
        self._hostname = get_hostname(config)
        self._prefix = "datadog-{0}".format(self._hostname)

    # On Unix system, check that the user is root (to call supervisorctl & status)
    # Otherwise emit a warning, and ask for confirmation
    @staticmethod
    def check_user_rights():
        if Platform.is_unix() and not os.geteuid() == 0:
            log.warning("You are not root, some information won't be collected")
            choice = raw_input('Are you sure you want to continue [y/N]? ')
            if choice.strip().lower() not in ['yes', 'y']:
                print 'Aborting'
                sys.exit(1)
            else:
                log.warn('Your user has to have at least read access'
                         ' to the logs and conf files of the agent')

    # Collect all conf and logs files and compress them
    def collect(self):
        if not self._api_key:
            raise Exception('No api_key found')
        log.info("Collecting logs and configuration files:")

        self._add_logs_tar()
        self._add_conf_tar()
        log.info("  * datadog-agent configcheck output")
        self._add_command_output_tar('configcheck.log', configcheck)
        log.info("  * datadog-agent status output")
        self._add_command_output_tar('status.log', self._supervisor_status)
        log.info("  * datadog-agent info output")
        self._add_command_output_tar('info.log', self._info_all)
        log.info("  * pip freeze")
        self._add_command_output_tar('freeze.log', self._pip_freeze)

        log.info("Saving all files to {0}".format(self._tar_path))
        self._tar.close()

    # Upload the tar file
    def upload(self):
        self._check_size()

        if self._cmdline:
            self._ask_for_confirmation()

        email = self._ask_for_email()

        log.info("Uploading {0} to Datadog Support".format(self._tar_path))
        url = self._url
        if self._case_id:
            url = '{0}/{1}'.format(self._url, str(self._case_id))
        url = "{0}?api_key={1}".format(url, self._api_key)
        files = {'flare_file': open(self._tar_path, 'rb')}
        data = {
            'case_id': self._case_id,
            'hostname': self._hostname,
            'email': email
        }
        self._resp = requests.post(url, files=files, data=data,
                                   timeout=self.TIMEOUT)
        self._analyse_result()

    # Start by creating the tar file which will contain everything
    def _init_tarfile(self):
        # Default temp path
        self._tar_path = os.path.join(
            tempfile.gettempdir(),
            self.COMPRESSED_FILE.format(strftime("%Y-%m-%d-%H-%M-%S"))
        )

        if os.path.exists(self._tar_path):
            os.remove(self._tar_path)
        self._tar = tarfile.open(self._tar_path, 'w:bz2')

    # Save logs file paths
    def _save_logs_path(self):
        prefix = ''
        if Platform.is_windows():
            prefix = 'windows_'
        config = get_logging_config()
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
            "{0}/*supervisord.log".format(os.path.dirname(self._collector_log))
        )

    def _add_log_file_tar(self, file_path):
        for f in glob.glob('{0}*'.format(file_path)):
            if self._can_read(f):
                self._tar.add(
                    f,
                    os.path.join(self._prefix, 'log', os.path.basename(f))
                )

    # Collect all conf
    def _add_conf_tar(self):
        conf_path = get_config_path()
        if self._can_read(conf_path):
            self._tar.add(
                self._strip_comment(conf_path),
                os.path.join(self._prefix, 'etc', 'datadog.conf')
            )

        if not Platform.is_windows():
            supervisor_path = os.path.join(
                os.path.dirname(get_config_path()),
                'supervisor.conf'
            )
            if self._can_read(supervisor_path):
                self._tar.add(
                    self._strip_comment(supervisor_path),
                    os.path.join(self._prefix, 'etc', 'supervisor.conf')
                )

        for file_path in glob.glob(os.path.join(get_confd_path(), '*.yaml')) +\
                glob.glob(os.path.join(get_confd_path(), '*.yaml.default')):
            if self._can_read(file_path, output=False):
                self._add_clean_confd(file_path)

    # Check if the file is readable (and log it)
    @classmethod
    def _can_read(cls, f, output=True):
        if os.access(f, os.R_OK):
            if output:
                log.info("  * {0}".format(f))
            return True
        else:
            log.warn("  * not readable - {0}".format(f))
            return False

    # Return path to a temp file without comment
    def _strip_comment(self, file_path):
        _, temp_path = tempfile.mkstemp(prefix='dd')
        atexit.register(os.remove, temp_path)
        with open(temp_path, 'w') as temp_file:
            with open(file_path, 'r') as orig_file:
                for line in orig_file.readlines():
                    if not self.COMMENT_REGEX.match(line):
                        temp_file.write(re.sub(self.APIKEY_REGEX, self.REPLACE_APIKEY, line))

        return temp_path

    # Remove password before collecting the file
    def _add_clean_confd(self, file_path):
        basename = os.path.basename(file_path)

        temp_path, password_found = self._strip_password(file_path)
        log.info("  * {0}{1}".format(file_path, password_found))
        self._tar.add(
            temp_path,
            os.path.join(self._prefix, 'etc', 'conf.d', basename)
        )

    # Return path to a temp file without password and comment
    def _strip_password(self, file_path):
        _, temp_path = tempfile.mkstemp(prefix='dd')
        atexit.register(os.remove, temp_path)
        with open(temp_path, 'w') as temp_file:
            with open(file_path, 'r') as orig_file:
                password_found = ''
                for line in orig_file.readlines():
                    if self.PASSWORD_REGEX.match(line):
                        line = re.sub(self.PASSWORD_REGEX, r'\1 ********', line)
                        password_found = ' - this file contains a password which '\
                                         'has been removed in the version collected'
                    if not self.COMMENT_REGEX.match(line):
                        temp_file.write(line)

        return temp_path, password_found

    # Add output of the command to the tarfile
    def _add_command_output_tar(self, name, command):
        temp_path = os.path.join(tempfile.gettempdir(), name)
        if os.path.exists(temp_path):
            os.remove(temp_path)
        backup_out, backup_err = sys.stdout, sys.stderr
        backup_handlers = logging.root.handlers[:]
        out, err = StringIO.StringIO(), StringIO.StringIO()
        sys.stdout, sys.stderr = out, err
        command()
        sys.stdout, sys.stderr = backup_out, backup_err
        logging.root.handlers = backup_handlers
        with open(temp_path, 'w') as temp_file:
            temp_file.write(">>>> STDOUT <<<<\n")
            temp_file.write(out.getvalue())
            out.close()
            temp_file.write(">>>> STDERR <<<<\n")
            temp_file.write(err.getvalue())
            err.close()
        self._tar.add(temp_path, os.path.join(self._prefix, name))
        os.remove(temp_path)

    # Print supervisor status (and nothing on windows)
    def _supervisor_status(self):
        if Platform.is_windows():
            print 'Windows - status not implemented'
        else:
            agent_exec = self._get_path_agent_exec()
            print '{0} status'.format(agent_exec)
            self._print_output_command([agent_exec, 'status'])
            supervisor_exec = self._get_path_supervisor_exec()
            print '{0} status'.format(supervisor_exec)
            self._print_output_command([supervisor_exec,
                                        '-c', self._get_path_supervisor_conf(),
                                        'status'])

    # Find the agent exec (package or source)
    def _get_path_agent_exec(self):
        agent_exec = '/etc/init.d/datadog-agent'
        if not os.path.isfile(agent_exec):
            agent_exec = os.path.join(
                os.path.dirname(os.path.realpath(__file__)),
                '../../bin/agent'
            )
        return agent_exec

    # Find the supervisor exec (package or source)
    def _get_path_supervisor_exec(self):
        supervisor_exec = '/opt/datadog-agent/bin/supervisorctl'
        if not os.path.isfile(supervisor_exec):
            supervisor_exec = os.path.join(
                os.path.dirname(os.path.realpath(__file__)),
                '../../venv/bin/supervisorctl'
            )
        return supervisor_exec

    # Find the supervisor conf (package or source)
    def _get_path_supervisor_conf(self):
        supervisor_conf = '/etc/dd-agent/supervisor.conf'
        if not os.path.isfile(supervisor_conf):
            supervisor_conf = os.path.join(
                os.path.dirname(os.path.realpath(__file__)),
                '../../supervisord/supervisord.conf'
            )
        return supervisor_conf

    # Print output of command
    def _print_output_command(self, command):
        try:
            status = subprocess.check_output(command, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError, e:
            status = 'Not able to get ouput, exit number {0}, exit ouput:\n'\
                     '{1}'.format(str(e.returncode), e.output)
        print status

    # Print info of all agent components
    def _info_all(self):
        CollectorStatus.print_latest_status(verbose=True)
        DogstatsdStatus.print_latest_status(verbose=True)
        ForwarderStatus.print_latest_status(verbose=True)

    # Run a pip freeze
    def _pip_freeze(self):
        try:
            import pip
            pip.main(['freeze', '--no-cache-dir'])
        except ImportError:
            print 'Unable to import pip'

    # Check if the file is not too big before upload
    def _check_size(self):
        if os.path.getsize(self._tar_path) > self.MAX_UPLOAD_SIZE:
            log.info("{0} won't be uploaded, its size is too important.\n"
                     "You can send it directly to support by mail.")
            sys.exit(1)

    # Function to ask for confirmation before upload
    def _ask_for_confirmation(self):
        print '{0} is going to be uploaded to Datadog.'.format(self._tar_path)
        choice = raw_input('Do you want to continue [Y/n]? ')
        if choice.strip().lower() not in ['yes', 'y', '']:
            print 'Aborting (you can still use {0})'.format(self._tar_path)
            sys.exit(1)

    # Ask for email if needed
    def _ask_for_email(self):
        # We ask everytime now, as it is also the 'id' to check
        # that the case is the good one if it exists
        return raw_input('Please enter your email: ').lower()

    # Print output (success/error) of the request
    def _analyse_result(self):
        # First catch our custom explicit 400
        if self._resp.status_code == 400:
            raise Exception('Your request is incorrect: {0}'.format(self._resp.json()['error']))
        # Then raise potential 500 and 404
        self._resp.raise_for_status()
        try:
            json_resp = self._resp.json()
        # Failed parsing
        except ValueError:
            raise Exception('An unknown error has occured - '
                            'Please contact support by email')
        # Finally, correct
        log.info("Your logs were successfully uploaded. For future reference,"
                 " your internal case id is {0}".format(json_resp['case_id']))
