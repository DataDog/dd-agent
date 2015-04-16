"""
This class handles the agent configuration.
"""
from config.paths import get_extra_checksd_path

GENERAL_OPTIONS = [
    StringOption('hostname'
        comment="Force the hostname to be that string. Otherwise auto-detected."
    ),
    BoolOption('use_ec2_instance_id',
        comment="If set to true, the agent will try to query and use its EC2 instance ID",
        default=False
    ),
    APIKeyOption('api_key',
        comment="API key used to auth on Datadog"
    ),
    URLOption('dd_url',
        comment="Datadog intake URL where the agent data will be forwarded",
        default="https://app.datadoghq.com",
        trailing_slash=False
    ),
    BoolOption('non_local_traffic',
        comment="forwarder/dogstatsd binds on all interfaces if true otherwise just on localhost",
        default=False
    ),
    HistogramPercOptions('histogram_percentiles',
        comment="Customize the percentiles used in histograms by the agent aggregators",
        default="0.95"
    ),
    HistogramAggrOptions('histogram_aggregates',
        comment="Customize the aggregate functions used in histograms by the agent aggregators\n"
                "Available: min, max, median, avg, count",
        default="max, median, avg, count"
    ),
    BoolOption('watchdog',
        comment="Use a watchdog to cap execution-time/memory, agent will self-destruct in that case",
        default=False
    )
]


FORWARDER_OPTIONS = [
    URLOption('listen_port',
        comment="Listens for traffic on this port and flushes data to `dd_url`"
        default=17123,
    ),
    PortOption('graphite_listen_port',
        comment="Register a Graphite listener on this port",
        default=None
    ),
]


COLLECTOR_OPTIONS = [
    IntegerOption('check_freq',
        comment="Collector main loop frequency",
        default=15,
        exposed=False
    ),
    PathOption('additional_checksd',
        comment="Additional folder to store custom checks that will
be run by the collector. They will also need to have an active
configuration file to be properly executed.""",
        default=get_default_checksd_path()
    ),
    BoolOption('autorestart',
        comment="Launches a supervisor to autorestart daemons on failures",
        default=False,
        deprecated=True
    ),
    BoolOption('check_timings',
        comment="Outputs a gauge `datadog.agent.check_run_time` per check",
        default=True
    )
]


SYSTEM_CHECKS_OPTIONS = [
    BoolOption('exclude_process_args',
        comment="Exclude process arguments (`ww` in `ps` command) from info sent to Datadog"
        default=False
    ),
    BoolOption('use_mount',
        comment="Use mount path instead of device name in disk check",
        default=False
    ),
    RegexOption('device_blacklist_re',
        comment="Ignore devices matching this regex in disk check"
    )
    BoolOption('collect_ec2_tags',
        comment="Collect EC2 tags",
        default=False
    ),
]


DOGSTATSD_OPTIONS = [
    BoolOption('use_dogstatsd',
        comment="Toggle to disable running the dogstatsd server",
        default=True
    ),
    PortOption('dogstatsd_port',
        comment="Port on which dogstatsd binds. Make sure your client binds on the same port.",
        default=8125
    ),
    URLOption('dogstatsd_target',
        comment="""Where dogstatsd sends post-processed aggregated data.
By default it flushes data to the local agent (handling errors/timeouts).
You can also change it to target Datadog directly (https://app.datadoghq.com)"""
        default=None
    ),
    BoolOption('dogstatsd_use_ddurl',
        comment="Send dogstatsd data directly to the agent",
        default=False,
        deprecated=True,
        deprecation_msg="Will be removed in 5.6. Use a custom `dogstatsd_target` instead."
    ),
    StringOption('statsd_forward_host',
        comment="""Used to forward all packets received by dogstatsd to another
statsd server allowing dogstatsd to capture all data in between.
WARNING: Make sure you only send regular statsd packets, other
statsd servers might not be able to handle the dogstatsd protocol."""
        default=None,
        configdefault=8125
    )
    PortOption('statsd_forward_port',
        comment="To be used in combination with `statsd_forward_host`",
        default=None,
        configdefault=8125
    ),
    StringOption('statsd_metric_namespace',
        comment="""Use this option to prefix all your dogstatsd metric. If
the option here is set to `namespace` any `metric.sub.name` will become
`namespace.metric.sub.name` instead."""
        default=None
    )
    BoolOption('utf8_decoding',
        comment="""By default, dogstatsd supports only ASCII packets. However,
most (dog)statsd clients supporting UTF-8 encoding, this option
enables processing them. WARNING: this comes with a non-negligeable
~10% overhead. FIXME in new agent core."""
        default=False,
    )
]


LOGGING_CONFIG = [
    LogLevelOption('log_level',
        comment="Change agent global log level, default is INFO",
        default=logging.INFO
    ),
    BoolOption('log_to_syslog',
        comment="Send log output to syslog",
        default=False
    ),
    StringOption('syslog_host',
        comment="To be used with `log_to_syslog`. Defaults to /dev/log on Linux or /var/run/log on Mac"
    ),
    PortOption('syslog_port',
        comment="To be used with `syslog_host`"
    ),
    BoolOption('disable_file_logging',
        comment="Disable all file loggers. WARNING no log will be recorded unless you set `log_to_syslog` for instance",
        default=False
    ),
]
