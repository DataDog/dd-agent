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
    logging.CRITICAL : "SEVERE",
    logging.DEBUG : "ALL",
    logging.ERROR : "WARNING",
    logging.FATAL : "SEVERE",
    logging.INFO : "INFO",
    logging.WARN : "WARNING",
    logging.WARNING : "WARNING",
}

JMX_CHECKS = ['tomcat', 'activemq', 'solr', 'cassandra', 'jmx']
JMX_FETCH_JAR_NAME = "jmxfetch-0.0.1-SNAPSHOT-jar-with-dependencies.jar"

class JMXFetch(object):

	pid_file = PidFile("jmxfetch")
	pid_file_path = pid_file.get_path()

	@classmethod
	def init(cls, confd_path, agentConfig, logging_config, default_check_frequency):
		try:
			should_run, java_bin_path = JMXFetch.should_run(confd_path)

			if should_run:
				if JMXFetch.is_running():
					log.warning("JMXFetch is already running")
					JMXFetch.stop()

				JMXFetch.start(confd_path, agentConfig, logging_config, java_bin_path, default_check_frequency)
		except Exception, e:
			log.exception("Error while initiating JMXFetch")


	@classmethod
	def should_run(cls, confd_path):
		"""
    Return a tuple (jmx_check_configured, java_bin_path)

    jmx_check_configured: boolean that shows that either one of the 
    check in JMX_CHECKS is enabled or there is a configured check 
    that have the "is_jmx" flag enabled in its init_config

    java_bin_path: is the path to the java executable. It was 
    previously set in the "instance" part of the yaml file of the
    jmx check. So we need to parse yaml files to get it.
    We assume that this value is alwayws the same for every jmx check
    so we can return the first value returned
    """

		jmx_check_configured = False
		java_bin_path = None

		for conf in glob.glob(os.path.join(confd_path, '*.yaml')):

			if jmx_check_configured and java_bin_path is not None:
			    return (jmx_check_configured, java_bin_path)

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
			    instances = check_config.get('instances', [])

			    if init_config and instances:
			        if type(instances) != list or len(instances) == 0:
			            continue

			        init_config = check_config.get('init_config', {})
			        instances = check_config.get('instances', {})

			        if java_bin_path is None:
			            if init_config.get('java_bin_path'):
			            # We get the java bin path from the yaml file for backward compatibility purposes
			                java_bin_path = check_config.get('init_config').get('java_bin_path')

			            for instance in instances:
			                if instance and instance.get('java_bin_path'):
			                    java_bin_path = instance.get('java_bin_path')
			        
			        if not jmx_check_configured and (init_config.get('is_jmx') or check_name in JMX_CHECKS):
			            jmx_check_configured = True

		return (jmx_check_configured, java_bin_path)

	@classmethod
	def is_running(cls):
		try:
			pid = JMXFetch.pid_file.get_pid()
			if pid is None:
				return False

			os.kill(pid, 0) 
			# os.kill(pid, 0) will throw an exception if pid is not running 
			# and won't do anything otherwise
			return True
		except Exception:
			return False

	@classmethod
	def stop(cls):
		try:
			log.info("Killing JMX Fetch")
			os.kill(JMXFetch.pid_file.get_pid(), signal.SIGKILL)
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
	def start(cls, confd_path, agentConfig, logging_config, path_to_java, default_check_frequency):
		statsd_port = agentConfig.get('dogstatsd_port', "8125")

		log.info("Starting jmxfetch:")
		try:
		    path_to_java = path_to_java or "java"
		    path_to_jmxfetch = JMXFetch.get_path_to_jmxfetch()
		    path_to_status_file = os.path.join(tempfile.gettempdir(), "jmx_status.yaml")
		    
		    subprocess_args = [
		            path_to_java, # Path to the java bin
		            '-jar', 
		            '"%s"' % path_to_jmxfetch, # Path to the jmxfetch jar
		            '"%s"' % confd_path, # Path of the conf.d directory that will be read by jmxfetch
		            str(statsd_port), # Port on which the dogstatsd server is running, as jmxfetch send metrics using dogstatsd
		            str(default_check_frequency * 1000),  # Period of the main loop of jmxfetch in ms
		            '"%s"' % logging_config.get('jmxfetch_log_file'), # Path of the log file
		            JAVA_LOGGING_LEVEL.get(logging_config.get("log_level"), "INFO"),  # Log Level: Should be in ["ALL", "FINEST", "FINER", "FINE", "CONFIG", "INFO", "WARNING", "SEVERE"]
		            ",".join(["%s.yaml" % check for check in JMX_CHECKS]),
		            '"%s"' % path_to_status_file,
		        ]

		    log.info("Running %s" % " ".join(subprocess_args))
		    jmxfetch = subprocess.Popen(subprocess_args, stdout=subprocess.PIPE)
		    jmx_connector_pid = jmxfetch.pid
		    log.debug("JMX Fetch pid: %s" % jmx_connector_pid)
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


