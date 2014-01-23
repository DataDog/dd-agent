# std
import os
import logging
import glob
import signal
import subprocess
import tempfile

# datadog
from util import PidFile, yaml, yLoader, get_os

log = logging.getLogger(__name__)

JAVA_LOGGING_LEVEL = {
    logging.CRITICAL : "FATAL",
    logging.DEBUG : "DEBUG",
    logging.ERROR : "ERROR",
    logging.FATAL : "FATAL",
    logging.INFO : "INFO",
    logging.WARN : "WARN",
    logging.WARNING : "WARN",
}

JMX_CHECKS = ['tomcat', 'activemq', 'activemq_58', 'solr', 'cassandra', 'jmx']
JMX_FETCH_JAR_NAME = "jmxfetch-0.2.0-jar-with-dependencies.jar"
JMX_LIST_COMMANDS = ['list_everything', 'list_collected_attributes', 'list_matching_attributes', 'list_not_matching_attributes', 'list_limited_attributes']
JMX_COLLECT_COMMAND = 'collect'

class JMXFetch(object):

    pid_file = PidFile("jmxfetch")
    pid_file_path = pid_file.get_path()

    @classmethod
    def init(cls, confd_path, agentConfig, logging_config, default_check_frequency, command=None):
        try:
            jmx_checks, java_bin_path, java_options = JMXFetch.should_run(confd_path)

            if len(jmx_checks) > 0:
                if JMXFetch.is_running():
                    log.warning("JMXFetch is already running, restarting it.")
                    JMXFetch.stop()

                JMXFetch.start(confd_path, agentConfig, logging_config, java_bin_path, java_options, default_check_frequency,  jmx_checks, command)
        except Exception, e:
            log.exception("Error while initiating JMXFetch")


    @classmethod
    def should_run(cls, confd_path):
        """
    Return a tuple (jmx_checks, java_bin_path)

    jmx_checks: list of yaml files that are jmx checks 
    (they have the is_jmx flag enabled or they are in JMX_CHECKS)
    and that have at least one instance configured

    java_bin_path: is the path to the java executable. It was 
    previously set in the "instance" part of the yaml file of the
    jmx check. So we need to parse yaml files to get it.
    We assume that this value is alwayws the same for every jmx check
    so we can return the first value returned

    java_options: is string contains options that will be passed to java_bin_path
    We assume that this value is alwayws the same for every jmx check
    so we can return the first value returned
    """

        jmx_checks = []
        java_bin_path = None
        java_options = None

        for conf in glob.glob(os.path.join(confd_path, '*.yaml')):

            java_bin_path_is_set = java_bin_path is not None
            java_options_is_set = java_options is not None

            check_name = os.path.basename(conf).split('.')[0]

            if os.path.exists(conf):
                f = open(conf)
                try:
                    check_config = yaml.load(f.read(), Loader=yLoader)
                    assert check_config is not None
                    f.close()
                except Exception:
                    f.close()
                    log.error("Unable to parse yaml config in %s" % conf)
                    continue

                init_config = check_config.get('init_config', {})
                if init_config is None:
                    init_config = {}
                instances = check_config.get('instances', [])
                if instances is None:
                    instances = []

                if instances:
                    if type(instances) != list or len(instances) == 0:
                        continue

                    if java_bin_path is None:
                        if init_config and init_config.get('java_bin_path'):
                            # We get the java bin path from the yaml file for backward compatibility purposes
                            java_bin_path = init_config.get('java_bin_path')

                        else:
                            for instance in instances:
                                if instance and instance.get('java_bin_path'):
                                    java_bin_path = instance.get('java_bin_path')

                    if java_options is None:
                        if init_config and init_config.get('java_options'):
                            java_options = init_config.get('java_options')
                        else:
                            for instance in instances:
                                if instance and instance.get('java_options'):
                                    java_options = instance.get('java_options')

                    if init_config.get('is_jmx') or check_name in JMX_CHECKS:
                        jmx_checks.append(os.path.basename(conf))

        return (jmx_checks, java_bin_path, java_options)

    @classmethod
    def is_running(cls):
        try:
            pid = JMXFetch.pid_file.get_pid()
            if pid is None:
                return False
        except Exception:
            return False

        if get_os() != 'windows':
            try:
                os.kill(pid, 0)
                # os.kill(pid, 0) will throw an exception if pid is not running 
                # and won't do anything otherwise
                # It doesn't work on windows as signal.CTRL_C_EVENT is 0, it would quit the process
                return True
            except Exception, e:
                if "Errno 3" not in str(e):
                    log.debug("Couldn't determine if jmxterm is running. We suppose it's not. %s" % str(e))
                return False

        # Else we are on windows, we need another way to check if it's running
        try:
            import ctypes # Available from python2.5
            kernel32 = ctypes.windll.kernel32
            SYNCHRONIZE = 0x100000

            process = kernel32.OpenProcess(SYNCHRONIZE, 0, pid)
            if process != 0:
                kernel32.CloseHandle(process)
                return True
            else:
                return False

        except Exception, e:
            log.debug("Couldn't determine if jmxterm is running. We suppose it's not. %s" % str(e))
            return False

    @classmethod
    def stop(cls):
        try:
            pid = JMXFetch.pid_file.get_pid()
            if pid is None:
                log.error("Couldn't get jmxfetch pid.")
                return
        except Exception:
            log.error("Couldn't get jmxfetch pid.")
            return

        try:
            log.info("Killing JMX Fetch")
            os.kill(pid, signal.SIGTERM)
            JMXFetch.pid_file.clean()
            log.info("Success")
        except Exception:
            log.error("Couldn't kill jmxfetch pid %s" % pid)

    @classmethod
    def get_path_to_jmxfetch(cls):
        if get_os() != 'windows':
            return os.path.realpath(os.path.join(os.path.abspath(__file__), "..", "checks", "libs", JMX_FETCH_JAR_NAME))

        return os.path.realpath(os.path.join(os.path.abspath(__file__), "..", "..", "jmxfetch", JMX_FETCH_JAR_NAME))

    @classmethod
    def start(cls, confd_path, agentConfig, logging_config, path_to_java, java_run_opts, default_check_frequency, jmx_checks, command=None):
        statsd_port = agentConfig.get('dogstatsd_port', "8125")

        command = command or JMX_COLLECT_COMMAND
        if command == JMX_COLLECT_COMMAND:
            reporter = "statsd:%s" % str(statsd_port)
        else:
            reporter = "console"

        log.info("Starting jmxfetch:")
        jmx_connector_pid = None
        try:
            path_to_java = path_to_java or "java"
            java_run_opts = java_run_opts or ""
            path_to_jmxfetch = JMXFetch.get_path_to_jmxfetch()
            path_to_status_file = os.path.join(tempfile.gettempdir(), "jmx_status.yaml")
            
            subprocess_args = [
                path_to_java, # Path to the java bin
                '-jar',
                r"%s" % path_to_jmxfetch, # Path to the jmxfetch jar
                '--check_period', str(default_check_frequency * 1000),  # Period of the main loop of jmxfetch in ms
                '--conf_directory', r"%s" % confd_path, # Path of the conf.d directory that will be read by jmxfetch,
                '--log_level', JAVA_LOGGING_LEVEL.get(logging_config.get("log_level"), "INFO"),  # Log Level: Mapping from Python log level to log4j log levels
                '--log_location', r"%s" % logging_config.get('jmxfetch_log_file'), # Path of the log file
                '--reporter',  reporter, # Reporter to use
                '--status_location', r"%s" % path_to_status_file, # Path to the status file to write    
                command, # Name of the command          
            ]

            subprocess_args.insert(3, '--check')
            for check in jmx_checks:
                subprocess_args.insert(4, check)

            if java_run_opts:
                for opt in java_run_opts.split():
                    subprocess_args.insert(1,opt)

            log.info("Running %s" % " ".join(subprocess_args))
            if command == JMX_COLLECT_COMMAND:
                cls.subprocess = subprocess.Popen(subprocess_args, close_fds=True)
                jmx_connector_pid = cls.subprocess.pid
                log.debug("JMX Fetch pid: %s" % jmx_connector_pid)

            else:
                subprocess.call(subprocess_args)
            
        except OSError, e:
            jmx_connector_pid = None
            log.exception("Couldn't launch JMXTerm. Is java in your PATH?")
        except Exception, e:
            jmx_connector_pid = None
            log.exception("Couldn't launch JMXTerm")

        # Write pid to pid file
        if jmx_connector_pid is not None:
            try:
                fp = open(JMXFetch.pid_file_path, 'w+')
                fp.write(str(jmx_connector_pid))
                fp.close()
                os.chmod(JMXFetch.pid_file_path, 0644)
            except Exception, e:
                log.exception("Unable to write jmxfetch pidfile: %s" % JMXFetch.pid_file_path)


