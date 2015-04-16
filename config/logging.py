

def get_logging_config(cfg_path=None):
    system_os = get_os()
    if system_os != 'windows':
        logging_config = {
            'log_level': None,
            'collector_log_file': '/var/log/datadog/collector.log',
            'forwarder_log_file': '/var/log/datadog/forwarder.log',
            'dogstatsd_log_file': '/var/log/datadog/dogstatsd.log',
            'jmxfetch_log_file': '/var/log/datadog/jmxfetch.log',
            'log_to_event_viewer': False,
            'log_to_syslog': True,
            'syslog_host': None,
            'syslog_port': None,
        }
    else:
        collector_log_location = os.path.join(_windows_commondata_path(), 'Datadog', 'logs', 'collector.log')
        forwarder_log_location = os.path.join(_windows_commondata_path(), 'Datadog', 'logs', 'forwarder.log')
        dogstatsd_log_location = os.path.join(_windows_commondata_path(), 'Datadog', 'logs', 'dogstatsd.log')
        jmxfetch_log_file = os.path.join(_windows_commondata_path(), 'Datadog', 'logs', 'jmxfetch.log')
        logging_config = {
            'log_level': None,
            'windows_collector_log_file': collector_log_location,
            'windows_forwarder_log_file': forwarder_log_location,
            'windows_dogstatsd_log_file': dogstatsd_log_location,
            'jmxfetch_log_file': jmxfetch_log_file,
            'log_to_event_viewer': False,
            'log_to_syslog': False,
            'syslog_host': None,
            'syslog_port': None,
        }

    config_path = get_config_path(cfg_path, os_name=system_os)
    config = ConfigParser.ConfigParser()
    config.readfp(skip_leading_wsp(open(config_path)))

    if config.has_section('handlers') or config.has_section('loggers') or config.has_section('formatters'):
        if system_os == 'windows':
            config_example_file = "https://github.com/DataDog/dd-agent/blob/master/packaging/datadog-agent/win32/install_files/datadog_win32.conf"
        else:
            config_example_file = "https://github.com/DataDog/dd-agent/blob/master/datadog.conf.example"

        sys.stderr.write("""Python logging config is no longer supported and will be ignored.
            To configure logging, update the logging portion of 'datadog.conf' to match:
             '%s'.
             """ % config_example_file)

    for option in logging_config:
        if config.has_option('Main', option):
            logging_config[option] = config.get('Main', option)

    levels = {
        'CRITICAL': logging.CRITICAL,
        'DEBUG': logging.DEBUG,
        'ERROR': logging.ERROR,
        'FATAL': logging.FATAL,
        'INFO': logging.INFO,
        'WARN': logging.WARN,
        'WARNING': logging.WARNING,
    }

    return logging_config


def initialize_logging(logger_name):
    try:
        logging_config = get_logging_config()

        logging.basicConfig(
            format=get_log_format(logger_name),
            level=logging_config['log_level'] or logging.INFO,
        )

        log_file = logging_config.get('%s_log_file' % logger_name)
        if log_file is not None and not logging_config['disable_file_logging']:
            # make sure the log directory is writeable
            # NOTE: the entire directory needs to be writable so that rotation works
            if os.access(os.path.dirname(log_file), os.R_OK | os.W_OK):
                file_handler = logging.handlers.RotatingFileHandler(log_file, maxBytes=LOGGING_MAX_BYTES, backupCount=1)
                formatter = logging.Formatter(get_log_format(logger_name), get_log_date_format())
                file_handler.setFormatter(formatter)

                root_log = logging.getLogger()
                root_log.addHandler(file_handler)
            else:
                sys.stderr.write("Log file is unwritable: '%s'\n" % log_file)

        # set up syslog
        if logging_config['log_to_syslog']:
            try:
                from logging.handlers import SysLogHandler

                if logging_config['syslog_host'] is not None and logging_config['syslog_port'] is not None:
                    sys_log_addr = (logging_config['syslog_host'], logging_config['syslog_port'])
                else:
                    sys_log_addr = "/dev/log"
                    # Special-case macs
                    if sys.platform == 'darwin':
                        sys_log_addr = "/var/run/syslog"

                handler = SysLogHandler(address=sys_log_addr, facility=SysLogHandler.LOG_DAEMON)
                handler.setFormatter(logging.Formatter(get_syslog_format(logger_name), get_log_date_format()))
                root_log = logging.getLogger()
                root_log.addHandler(handler)
            except Exception, e:
                sys.stderr.write("Error setting up syslog: '%s'\n" % str(e))
                traceback.print_exc()

        # Setting up logging in the event viewer for windows
        if get_os() == 'windows' and logging_config['log_to_event_viewer']:
            try:
                from logging.handlers import NTEventLogHandler
                nt_event_handler = NTEventLogHandler(logger_name,get_win32service_file('windows', 'win32service.pyd'), 'Application')
                nt_event_handler.setFormatter(logging.Formatter(get_syslog_format(logger_name), get_log_date_format()))
                nt_event_handler.setLevel(logging.ERROR)
                app_log = logging.getLogger(logger_name)
                app_log.addHandler(nt_event_handler)
            except Exception, e:
                sys.stderr.write("Error setting up Event viewer logging: '%s'\n" % str(e))
                traceback.print_exc()

    except Exception, e:
        sys.stderr.write("Couldn't initialize logging: %s\n" % str(e))
        traceback.print_exc()

        # if config fails entirely, enable basic stdout logging as a fallback
        logging.basicConfig(
            format=get_log_format(logger_name),
            level=logging.INFO,
        )

    # re-get the log after logging is initialized
    global log
    log = logging.getLogger(__name__)
