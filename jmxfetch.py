# std
import glob
import logging
import os
import subprocess
import sys
import signal
import time

# datadog
from util import get_os, yLoader, yDumper
from config import get_config, get_confd_path, get_jmx_status_path, get_logging_config, \
    PathNotFound, DEFAULT_CHECK_FREQUENCY

# 3rd party
import yaml

log = logging.getLogger(__name__)

JAVA_LOGGING_LEVEL = {
    logging.CRITICAL: "FATAL",
    logging.DEBUG: "DEBUG",
    logging.ERROR: "ERROR",
    logging.FATAL: "FATAL",
    logging.INFO: "INFO",
    logging.WARN: "WARN",
    logging.WARNING: "WARN",
}

JMX_FETCH_JAR_NAME = "jmxfetch-0.5.2-jar-with-dependencies.jar"
_JVM_DEFAULT_MAX_MEMORY_ALLOCATION = " -Xmx200m"
_JVM_DEFAULT_INITIAL_MEMORY_ALLOCATION = " -Xms50m"
JMXFETCH_MAIN_CLASS = "org.datadog.jmxfetch.App"
JMX_CHECKS = [
    'activemq',
    'activemq_58',
    'cassandra',
    'jmx',
    'solr',
    'tomcat',
]
JMX_COLLECT_COMMAND = 'collect'
JMX_LIST_COMMANDS = {
    'list_everything': 'List every attributes available that has a type supported by JMXFetch',
    'list_collected_attributes': 'List attributes that will actually be collected by your current instances configuration',
    'list_matching_attributes': 'List attributes that match at least one of your instances configuration',
    'list_not_matching_attributes': "List attributes that don't match any of your instances configuration",
    'list_limited_attributes': "List attributes that do match one of your instances configuration but that are not being collected because it would exceed the number of metrics that can be collected",
    JMX_COLLECT_COMMAND: "Start the collection of metrics based on your current configuration and display them in the console"}

PYTHON_JMX_STATUS_FILE = 'jmx_status_python.yaml'

LINK_TO_DOC = "See http://docs.datadoghq.com/integrations/java/ for more information"


class InvalidJMXConfiguration(Exception):
    pass


class JMXFetch(object):
    """
    Start JMXFetch if any JMX check is configured
    """
    def __init__(self, confd_path, agentConfig):
        self.confd_path = confd_path
        self.agentConfig = agentConfig
        self.logging_config = get_logging_config()
        self.check_frequency = DEFAULT_CHECK_FREQUENCY

        self.jmx_process = None
        self.jmx_checks = None

    def terminate(self):
        self.jmx_process.terminate()

    def _handle_sigterm(self, signum, frame):
        # Terminate jmx process on SIGTERM signal
        log.debug("Caught sigterm. Stopping subprocess.")
        self.jmx_process.terminate()

    def register_signal_handlers(self):
        """
        Enable SIGTERM and SIGINT handlers
        """
        try:
            # Gracefully exit on sigterm
            signal.signal(signal.SIGTERM, self._handle_sigterm)

            # Handle Keyboard Interrupt
            signal.signal(signal.SIGINT, self._handle_sigterm)

        except ValueError:
            log.exception("Unable to register signal handlers.")

    def configure(self, check_list=None):
        """
        Instantiate JMXFetch parameters.
        """
        self.jmx_checks, self.invalid_checks, self.java_bin_path, self.java_options, self.tools_jar_path = \
            self.get_configuration(check_list)

    def should_run(self):
        """
        Should JMXFetch run ?
        """
        return self.jmx_checks is not None and self.jmx_checks != []

    def run(self, command=None, check_list=None, reporter=None):

        if check_list or self.jmx_checks is None:
            # (Re)set/(re)configure JMXFetch parameters when `check_list` is specified or
            # no configuration was found
            self.configure(check_list)

        try:
            command = command or JMX_COLLECT_COMMAND

            if len(self.invalid_checks) > 0:
                try:
                    self._write_status_file(self.invalid_checks)
                except Exception:
                    log.exception("Error while writing JMX status file")

            if len(self.jmx_checks) > 0:
                return self._start(self.java_bin_path, self.java_options, self.jmx_checks,
                                   command, reporter, self.tools_jar_path)
            else:
                # We're exiting purposefully, so exit with zero (supervisor's expected
                # code). HACK: Sleep a little bit so supervisor thinks we've started cleanly
                # and thus can exit cleanly.
                time.sleep(4)
                log.info("No valid JMX integration was found. Exiting ...")
        except Exception:
            log.exception("Error while initiating JMXFetch")
            raise

    def get_configuration(self, checks_list=None):
        """
        Return a tuple (jmx_checks, invalid_checks, java_bin_path, java_options)

        jmx_checks: list of yaml files that are jmx checks
        (they have the is_jmx flag enabled or they are in JMX_CHECKS)
        and that have at least one instance configured

        invalid_checks: dictionary whose keys are check names that are JMX checks but
        they have a bad configuration. Values of the dictionary are exceptions generated
        when checking the configuration

        java_bin_path: is the path to the java executable. It was
        previously set in the "instance" part of the yaml file of the
        jmx check. So we need to parse yaml files to get it.
        We assume that this value is alwayws the same for every jmx check
        so we can return the first value returned

        java_options: is string contains options that will be passed to java_bin_path
        We assume that this value is alwayws the same for every jmx check
        so we can return the first value returned

        tools_jar_path:  Path to tools.jar, which is only part of the JDK and that is
        required to connect to a local JMX instance using the attach api.
        """
        jmx_checks = []
        java_bin_path = None
        java_options = None
        tools_jar_path = None
        invalid_checks = {}

        for conf in glob.glob(os.path.join(self.confd_path, '*.yaml')):
            filename = os.path.basename(conf)
            check_name = filename.split('.')[0]

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

                try:
                    is_jmx, check_java_bin_path, check_java_options, check_tools_jar_path = \
                        self._is_jmx_check(check_config, check_name, checks_list)
                    if is_jmx:
                        jmx_checks.append(filename)
                        if java_bin_path is None and check_java_bin_path is not None:
                            java_bin_path = check_java_bin_path
                        if java_options is None and check_java_options is not None:
                            java_options = check_java_options
                        if tools_jar_path is None and check_tools_jar_path is not None:
                            tools_jar_path = check_tools_jar_path
                except InvalidJMXConfiguration, e:
                    log.error("%s check does not have a valid JMX configuration: %s" % (check_name, e))
                    # Make sure check_name is a string - Fix issues with Windows
                    check_name = check_name.encode('ascii', 'ignore')
                    invalid_checks[check_name] = str(e)

        return (jmx_checks, invalid_checks, java_bin_path, java_options, tools_jar_path)

    def _start(self, path_to_java, java_run_opts, jmx_checks, command, reporter, tools_jar_path):
        statsd_port = self.agentConfig.get('dogstatsd_port', "8125")
        if reporter is None:
            reporter = "statsd:%s" % str(statsd_port)

        log.info("Starting jmxfetch:")
        try:
            path_to_java = path_to_java or "java"
            java_run_opts = java_run_opts or ""
            path_to_jmxfetch = self._get_path_to_jmxfetch()
            path_to_status_file = os.path.join(get_jmx_status_path(), "jmx_status.yaml")

            if tools_jar_path is None:
                classpath = path_to_jmxfetch
            else:
                classpath = r"%s:%s" % (tools_jar_path, path_to_jmxfetch)

            subprocess_args = [
                path_to_java,  # Path to the java bin
                '-classpath',
                classpath,
                JMXFETCH_MAIN_CLASS,
                '--check_period', str(self.check_frequency * 1000),  # Period of the main loop of jmxfetch in ms
                '--conf_directory', r"%s" % self.confd_path,  # Path of the conf.d directory that will be read by jmxfetch,
                '--log_level', JAVA_LOGGING_LEVEL.get(self.logging_config.get("log_level"), "INFO"),  # Log Level: Mapping from Python log level to log4j log levels
                '--log_location', r"%s" % self.logging_config.get('jmxfetch_log_file'),  # Path of the log file
                '--reporter', reporter,  # Reporter to use
                '--status_location', r"%s" % path_to_status_file,  # Path to the status file to write
                command,  # Name of the command
            ]

            subprocess_args.insert(4, '--check')
            for check in jmx_checks:
                subprocess_args.insert(5, check)

            # Specify a maximum memory allocation pool for the JVM
            if "Xmx" not in java_run_opts and "XX:MaxHeapSize" not in java_run_opts:
                java_run_opts += _JVM_DEFAULT_MAX_MEMORY_ALLOCATION
            # Specify the initial memory allocation pool for the JVM
            if "Xms" not in java_run_opts and "XX:InitialHeapSize" not in java_run_opts:
                java_run_opts += _JVM_DEFAULT_INITIAL_MEMORY_ALLOCATION

            for opt in java_run_opts.split():
                subprocess_args.insert(1, opt)

            log.info("Running %s" % " ".join(subprocess_args))
            jmx_process = subprocess.Popen(subprocess_args, close_fds=True)
            self.jmx_process = jmx_process
            
            # Register SIGINT and SIGTERM signal handlers
            self.register_signal_handlers()

            # Wait for JMXFetch to return
            jmx_process.wait()

            return jmx_process.returncode

        except OSError:
            java_path_msg = "Couldn't launch JMXTerm. Is Java in your PATH ?"
            log.exception(java_path_msg)
            invalid_checks = {}
            for check in jmx_checks:
                check_name = check.split('.')[0]
                check_name = check_name.encode('ascii', 'ignore')
                invalid_checks[check_name] = java_path_msg
            self._write_status_file(invalid_checks)
            raise
        except Exception:
            log.exception("Couldn't launch JMXFetch")
            raise

    def _write_status_file(self, invalid_checks):
        data = {
            'timestamp': time.time(),
            'invalid_checks': invalid_checks
        }
        stream = file(os.path.join(get_jmx_status_path(), PYTHON_JMX_STATUS_FILE), 'w')
        yaml.dump(data, stream, Dumper=yDumper)
        stream.close()

    def _is_jmx_check(self, check_config, check_name, checks_list):
        init_config = check_config.get('init_config', {}) or {}
        java_bin_path = None
        java_options = None
        is_jmx = False
        is_attach_api = False
        tools_jar_path = init_config.get("tools_jar_path")

        if init_config is None:
            init_config = {}

        if checks_list:
            if check_name in checks_list:
                is_jmx = True

        elif init_config.get('is_jmx') or check_name in JMX_CHECKS:
            is_jmx = True

        if is_jmx:
            instances = check_config.get('instances', [])
            if type(instances) != list or len(instances) == 0:
                raise InvalidJMXConfiguration("You need to have at least one instance "
                                              "defined in the YAML file for this check")

            for inst in instances:
                if type(inst) != dict:
                    raise InvalidJMXConfiguration("Each instance should be"
                                                  " a dictionary. %s" % LINK_TO_DOC)
                host = inst.get('host', None)
                port = inst.get('port', None)
                conf = inst.get('conf', init_config.get('conf', None))
                tools_jar_path = inst.get('tools_jar_path')

                # Support for attach api using a process name regex
                proc_regex = inst.get('process_name_regex')

                if proc_regex is not None:
                    is_attach_api = True
                else:
                    if host is None:
                        raise InvalidJMXConfiguration("A host must be specified")
                    if port is None or type(port) != int:
                        raise InvalidJMXConfiguration("A numeric port must be specified")

                if conf is None:
                    log.warning("%s doesn't have a 'conf' section. Only basic JVM metrics"
                                " will be collected. %s" % (inst, LINK_TO_DOC))
                else:
                    if type(conf) != list or len(conf) == 0:
                        raise InvalidJMXConfiguration("'conf' section should be a list"
                                                      " of configurations %s" % LINK_TO_DOC)

                    for config in conf:
                        include = config.get('include', None)
                        if include is None:
                            raise InvalidJMXConfiguration("Each configuration must have an"
                                                          " 'include' section. %s" % LINK_TO_DOC)

                        if type(include) != dict:
                            raise InvalidJMXConfiguration("'include' section must"
                                                          " be a dictionary %s" % LINK_TO_DOC)

            if java_bin_path is None:
                if init_config and init_config.get('java_bin_path'):
                    # We get the java bin path from the yaml file
                    # for backward compatibility purposes
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

            if is_attach_api:
                if tools_jar_path is None:
                    for instance in instances:
                        if instance and instance.get("tools_jar_path"):
                            tools_jar_path = instance.get("tools_jar_path")

                if tools_jar_path is None:
                    raise InvalidJMXConfiguration("You must specify the path to tools.jar"
                                                  " in your JDK.")
                elif not os.path.isfile(tools_jar_path):
                    raise InvalidJMXConfiguration("Unable to find tools.jar at %s" % tools_jar_path)
            else:
                tools_jar_path = None

        return is_jmx, java_bin_path, java_options, tools_jar_path

    def _get_path_to_jmxfetch(self):
        if get_os() != 'windows':
            return os.path.realpath(os.path.join(os.path.abspath(__file__), "..", "checks",
                                    "libs", JMX_FETCH_JAR_NAME))
        return os.path.realpath(os.path.join(os.path.abspath(__file__), "..", "..",
                                "jmxfetch", JMX_FETCH_JAR_NAME))


def init(config_path=None):
    agentConfig = get_config(parse_args=False, cfg_path=config_path)
    osname = get_os()
    try:
        confd_path = get_confd_path(osname)
    except PathNotFound, e:
        log.error("No conf.d folder found at '%s' or in the directory where"
                  "the Agent is currently deployed.\n" % e.args[0])

    return confd_path, agentConfig


def main(config_path=None):
    """ JMXFetch main entry point """
    confd_path, agentConfig = init(config_path)

    jmx = JMXFetch(confd_path, agentConfig)
    return jmx.run()

if __name__ == '__main__':
    sys.exit(main())
