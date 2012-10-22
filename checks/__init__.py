"""Base class for Checks.

If you are writing your own checks you should subclass the Check class.

The typicall workflow works like this:
1. Create your Check class
2. Declare your metrics as gauges or counters
3. Call save_sample for each metric
4. Call get_metrics() to get results
5. Plug the results into checks/common.py

"""

import logging
import re
import socket
import time
import types
import os

try:
    from hashlib import md5
except ImportError:
    import md5

# Konstants
class CheckException(Exception): pass
class Infinity(CheckException): pass
class NaN(CheckException): pass
class UnknownValue(CheckException): pass

class LaconicFilter(logging.Filter):
    """
    Filters messages, only print them once while keeping memory under control
    """
    LACONIC_MEM_LIMIT = 1024

    def __init__(self, name=""):
        logging.Filter.__init__(self, name)
        self.hashed_messages = {}

    def hash(self, msg):
        return md5(msg).hexdigest()

    def filter(self, record):
        try:
            h = self.hash(record.getMessage())
            if h in self.hashed_messages:
                return 0
            else:
                # Don't blow up our memory
                if len(self.hashed_messages) >= LaconicFilter.LACONIC_MEM_LIMIT:
                    self.hashed_messages.clear()
                self.hashed_messages[h] = True
                return 1
        except:
            return 1

class Check(object):
    """
    (Abstract) class for all checks with the ability to:
    * store 1 (and only 1) sample for gauges per metric/tag combination
    * compute rates for counters
    * only log error messages once (instead of each time they occur)

    """
    def __init__(self, logger):
        # where to store samples, indexed by metric_name
        # metric_name: {("sorted", "tags"): [(ts, value), (ts, value)],
        #                 tuple(tags) are stored as a key since lists are not hashable
        #               None: [(ts, value), (ts, value)]}
        #                 untagged values are indexed by None
        self._sample_store = {}
        self._counters = {} # metric_name: bool
        self.logger = logger
        try:
            self.logger.addFilter(LaconicFilter())
        except:
            self.logger.exception("Trying to install laconic log filter and failed")

    def normalize(self, metric, prefix=None):
        """Turn a metric into a well-formed metric name
        prefix.b.c
        """
        name = re.sub(r"[,\+\*\-/()\[\]{}]", "_", metric)
        # Eliminate multiple _
        name = re.sub(r"__+", "_", name)
        # Don't start/end with _
        name = re.sub(r"^_", "", name)
        name = re.sub(r"_$", "", name)
        # Drop ._ and _.
        name = re.sub(r"\._", ".", name)
        name = re.sub(r"_\.", ".", name)

        if prefix is not None:
            return prefix + "." + name
        else:
            return name

    def normalize_device_name(self, device_name):
        return device_name.strip().lower().replace(' ', '_')

    def counter(self, metric):
        """
        Treats the metric as a counter, i.e. computes its per second derivative
        ACHTUNG: Resets previous values associated with this metric.
        """
        self._counters[metric] = True
        self._sample_store[metric] = {}

    def is_counter(self, metric):
        "Is this metric a counter?"
        return metric in self._counters

    def gauge(self, metric):
        """
        Treats the metric as a gauge, i.e. keep the data as is
        ACHTUNG: Resets previous values associated with this metric.
        """
        self._sample_store[metric] = {}

    def is_metric(self, metric):
        return metric in self._sample_store

    def is_gauge(self, metric):
        return self.is_metric(metric) and \
               not self.is_counter(metric)

    def get_metric_names(self):
        "Get all metric names"
        return self._sample_store.keys()

    def save_gauge(self, metric, value, timestamp=None, tags=None, hostname=None, device_name=None):
        """ Save a gauge value. """
        if not self.is_gauge(metric):
            self.gauge(metric)
        self.save_sample(metric, value, timestamp, tags, hostname, device_name)

    def save_sample(self, metric, value, timestamp=None, tags=None, hostname=None, device_name=None):
        """Save a simple sample, evict old values if needed
        """
        from util import cast_metric_val

        if timestamp is None:
            timestamp = time.time()
        if metric not in self._sample_store:
            raise CheckException("Saving a sample for an undefined metric: %s" % metric)
        try:
            value = cast_metric_val(value)
        except ValueError, ve:
            raise NaN(ve)

        # Sort and validate tags
        if tags is not None:
            if type(tags) not in [type([]), type(())]:
                raise CheckException("Tags must be a list or tuple of strings")
            else:
                tags = tuple(sorted(tags))

        # Data eviction rules
        key = (tags, device_name)
        if self.is_gauge(metric):
            self._sample_store[metric][key] = ((timestamp, value, hostname, device_name), )
        elif self.is_counter(metric):
            if self._sample_store[metric].get(key) is None:
                self._sample_store[metric][key] = [(timestamp, value, hostname, device_name)]
            else:
                self._sample_store[metric][key] = self._sample_store[metric][key][-1:] + [(timestamp, value, hostname, device_name)]
        else:
            raise CheckException("%s must be either gauge or counter, skipping sample at %s" % (metric, time.ctime(timestamp)))

        if self.is_gauge(metric):
            # store[metric][tags] = (ts, val) - only 1 value allowed
            assert len(self._sample_store[metric][key]) == 1, self._sample_store[metric]
        elif self.is_counter(metric):
            assert len(self._sample_store[metric][key]) in (1, 2), self._sample_store[metric]

    @classmethod
    def _rate(cls, sample1, sample2):
        "Simple rate"
        try:
            interval = sample2[0] - sample1[0]
            if interval == 0:
                raise Infinity()

            delta = sample2[1] - sample1[1]
            if delta < 0:
                raise UnknownValue()

            return (sample2[0], delta / interval, sample2[2], sample2[3])
        except Infinity:
            raise 
        except UnknownValue:
            raise 
        except Exception, e:
            raise NaN(e)

    def get_sample_with_timestamp(self, metric, tags=None, device_name=None):
        "Get (timestamp-epoch-style, value)"

        # Get the proper tags
        if tags is not None and type(tags) == type([]):
            tags.sort()
            tags = tuple(tags)
        key = (tags, device_name)

        # Never seen this metric
        if metric not in self._sample_store:
            raise UnknownValue()

        # Not enough value to compute rate
        elif self.is_counter(metric) and len(self._sample_store[metric][key]) < 2:
            raise UnknownValue()

        elif self.is_counter(metric) and len(self._sample_store[metric][key]) >= 2:
            return self._rate(self._sample_store[metric][key][-2], self._sample_store[metric][key][-1])

        elif self.is_gauge(metric) and len(self._sample_store[metric][key]) >= 1:
            return self._sample_store[metric][key][-1]

        else:
            raise UnknownValue()

    def get_sample(self, metric, tags=None, device_name=None):
        "Return the last value for that metric"
        x = self.get_sample_with_timestamp(metric, tags, device_name)
        assert type(x) == types.TupleType and len(x) == 4, x
        return x[1]

    def get_samples_with_timestamps(self):
        "Return all values {metric: (ts, value)} for non-tagged metrics"
        values = {}
        for m in self._sample_store:
            try:
                values[m] = self.get_sample_with_timestamp(m)
            except:
                pass
        return values

    def get_samples(self):
        "Return all values {metric: value} for non-tagged metrics"
        values = {}
        for m in self._sample_store:
            try:
                # Discard the timestamp
                values[m] = self.get_sample_with_timestamp(m)[1]
            except:
                pass
        return values

    def get_metrics(self):
        """Get all metrics, including the ones that are tagged.
        This is the preferred method to retrieve metrics

        @return the list of samples
        @rtype [(metric_name, timestamp, value, {"tags": ["tag1", "tag2"]}), ...]
        """
        metrics = []
        for m in self._sample_store:
            try:
                for key in self._sample_store[m]:
                    tags, device_name = key
                    try:
                        ts, val, hostname, device_name = self.get_sample_with_timestamp(m, tags, device_name)
                    except UnknownValue:
                        continue
                    attributes = {}
                    if tags:
                        attributes['tags'] = list(tags)
                    if hostname:
                        attributes['host_name'] = hostname
                    if device_name:
                        attributes['device_name'] = device_name
                    metrics.append((m, int(ts), val, attributes))
            except:
                pass
        return metrics

class AgentCheck(object):
    def __init__(self, name, init_config, agentConfig):
        """
        Initialize a new check.

        :param name: The name of the check
        :param init_config: The config for initializing the check
        :param agentConfig: The global configuration for the agent
        """
        from aggregator import MetricsAggregator


        self.name = name
        self.init_config = init_config
        self.agentConfig = agentConfig
        self.hostname = gethostname(agentConfig)
        self.log = logging.getLogger('checks.%s' % name)
        self.aggregator = MetricsAggregator(self.hostname, formatter=agent_formatter)
        self.events = []

    def gauge(self, metric, value, tags=None, hostname=None, device_name=None, timestamp=None):
        """
        Record the value of a gauge, with optional tags, hostname and device
        name.

        :param metric: The name of the metric
        :param value: The value of the gauge
        :param tags: (optional) A list of tags for this metric
        :param hostname: (optional) A hostname for this metric. Defaults to the current hostname.
        :param device_name: (optional) The device name for this metric
        :param timestamp: (optional) The timestamp for this metric value
        """
        self.aggregator.gauge(metric, value, tags, hostname, device_name, timestamp)

    def increment(self, metric, value=1, tags=None, hostname=None, device_name=None):
        """
        Increment a counter with optional tags, hostname and device name.

        :param metric: The name of the metric
        :param value: The value to increment by
        :param tags: (optional) A list of tags for this metric
        :param hostname: (optional) A hostname for this metric. Defaults to the current hostname.
        :param device_name: (optional) The device name for this metric
        """
        self.aggregator.increment(metric, value, tags, hostname, device_name)

    def decrement(self, metric, value=-1, tags=None, hostname=None, device_name=None):
        """
        Increment a counter with optional tags, hostname and device name.

        :param metric: The name of the metric
        :param value: The value to decrement by
        :param tags: (optional) A list of tags for this metric
        :param hostname: (optional) A hostname for this metric. Defaults to the current hostname.
        :param device_name: (optional) The device name for this metric
        """
        self.aggregator.decrement(metric, value, tags, hostname, device_name)

    def rate(self, metric, value, tags=None, hostname=None, device_name=None):
        """
        Submit a point for a metric that will be calculated as a rate on flush.
        Values will persist across each call to `check` if there is not enough
        point to generate a rate on the flush.

        :param metric: The name of the metric
        :param value: The value of the rate
        :param tags: (optional) A list of tags for this metric
        :param hostname: (optional) A hostname for this metric. Defaults to the current hostname.
        :param device_name: (optional) The device name for this metric
        """
        self.aggregator.rate(metric, value, tags, hostname, device_name)

    def histogram(self, metric, value, tags=None, hostname=None, device_name=None):
        """
        Sample a histogram value, with optional tags, hostname and device name.

        :param metric: The name of the metric
        :param value: The value to sample for the histogram
        :param tags: (optional) A list of tags for this metric
        :param hostname: (optional) A hostname for this metric. Defaults to the current hostname.
        :param device_name: (optional) The device name for this metric
        """
        self.aggregator.histogram(metric, value, tags, hostname, device_name)

    def set(self, metric, value, tags=None, hostname=None, device_name=None):
        """
        Sample a set value, with optional tags, hostname and device name.

        :param metric: The name of the metric
        :param value: The value for the set
        :param tags: (optional) A list of tags for this metric
        :param hostname: (optional) A hostname for this metric. Defaults to the current hostname.
        :param device_name: (optional) The device name for this metric
        """
        self.aggregator.set(metric, value, tags, hostname, device_name)

    def event(self, event):
        """
        Save an event.

        :param event: The event payload as a dictionary. Has the following
        structure:

            {
                "timestamp": int, the epoch timestamp for the event,
                "event_type": string, the event time name,
                "api_key": string, the api key of the account to associate the event with,
                "msg_title": string, the title of the event,
                "msg_text": string, the text body of the event,
                "alert_type": (optional) string, one of ('error', 'warning', 'success', 'info').
                    Defaults to 'info'.
                "source_type_name": (optional) string, the source type name,
                "host": (optional) string, the name of the host,
                "tags": (optional) list, a list of tags to associate with this event
            }
        """
        self.events.append(event)

    def has_events(self):
        """
        Check whether the check has saved any events

        @return whether or not the check has saved any events
        @rtype boolean
        """
        return len(self.events) > 0

    def get_metrics(self):
        """
        Get all metrics, including the ones that are tagged.

        @return the list of samples
        @rtype [(metric_name, timestamp, value, {"tags": ["tag1", "tag2"]}), ...]
        """
        return self.aggregator.flush()

    def get_events(self):
        """
        Return a list of the events saved by the check, if any

        @return the list of events saved by this check
        @rtype list of event dictionaries
        """
        events = self.events
        self.events = []
        return events

    def check(self, instance):
        """
        Overriden by the check class. This will be called to run the check.

        :param instance: A dict with the instance information. This will vary
        depending on your config structure.
        """
        raise NotImplementedError()

    @classmethod
    def from_yaml(cls, path_to_yaml=None, agentConfig=None, yaml_text=None, check_name=None):
        """
        A method used for testing your check without running the agent.
        """
        from util import yaml, yLoader
        if path_to_yaml:
            check_name = os.path.basename(path_to_yaml).split('.')[0]
            try:
                f = open(path_to_yaml)
            except IOError:
                raise Exception('Unable to open yaml config: %s' % path_to_yaml)
            yaml_text = f.read()
            f.close()

        config = yaml.load(yaml_text, Loader=yLoader)
        check = cls(check_name, config.get('init_config') or {}, agentConfig or {})

        return check, config.get('instances', [])

def gethostname(agentConfig):
    if agentConfig.get("hostname") is not None:
        return agentConfig["hostname"]
    else:
        try:
            return socket.getfqdn()
        except socket.error, e:
            logging.debug("processes: unable to get hostname: " + str(e))

def agent_formatter(metric, value, timestamp, tags, hostname, device_name=None):
    """ Formats metrics coming from the MetricsAggregator. Will look like:
     (metric, timestamp, value, {"tags": ["tag1", "tag2"], ...})
    """
    attributes = {}
    if tags:
        attributes['tags'] = list(tags)
    if hostname:
        attributes['hostname'] = hostname
    if device_name:
        attributes['device_name'] = device_name
    if attributes:
        return (metric, int(timestamp), value, attributes)
    return (metric, int(timestamp), value)
