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

    def save_gauge(self, metric, value, timestamp=None, tags=None, hostname=None):
        """ Save a gauge value. """
        if not self.is_gauge(metric):
            self.gauge(metric)
        self.save_sample(metric, value, timestamp, tags, hostname)

    def save_sample(self, metric, value, timestamp=None, tags=None, hostname=None, device_name=None):
        """Save a simple sample, evict old values if needed
        """
        if timestamp is None:
            timestamp = time.time()
        if metric not in self._sample_store:
            raise CheckException("Saving a sample for an undefined metric: %s" % metric)
        try:
            value = float(value)
        except ValueError, ve:
            raise NaN(ve)
        
        # Sort and validate tags
        if tags is not None:
            if type(tags) not in [type([]), type(())]:
                raise CheckException("Tags must be a list or tuple of strings")
            else:
                tags = tuple(sorted(tags))

        # Data eviction rules
        if self.is_gauge(metric):
            self._sample_store[metric][tags] = ((timestamp, value, hostname, device_name), )
        elif self.is_counter(metric):
            if self._sample_store[metric].get(tags) is None:
                self._sample_store[metric][tags] = [(timestamp, value, hostname, device_name)]
            else:
                self._sample_store[metric][tags] = self._sample_store[metric][tags][-1:] + [(timestamp, value, hostname, device_name)]
        else:
            raise CheckException("%s must be either gauge or counter, skipping sample at %s" % (metric, time.ctime(timestamp)))

        if self.is_gauge(metric):
            # store[metric][tags] = (ts, val) - only 1 value allowd
            assert len(self._sample_store[metric][tags]) == 1, self._sample_store[metric]
        elif self.is_counter(metric):
            assert len(self._sample_store[metric][tags]) in (1, 2), self._sample_store[metric]

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

    def get_sample_with_timestamp(self, metric, tags=None):
        "Get (timestamp-epoch-style, value)"

        # Get the proper tags
        if tags is not None and type(tags) == type([]):
            tags.sort()
            tags = tuple(tags)

        # Never seen this metric
        if metric not in self._sample_store:
            raise UnknownValue()

        # Not enough value to compute rate
        elif self.is_counter(metric) and len(self._sample_store[metric][tags]) < 2:
            raise UnknownValue()
        
        elif self.is_counter(metric) and len(self._sample_store[metric][tags]) >= 2:
            return self._rate(self._sample_store[metric][tags][-2], self._sample_store[metric][tags][-1])

        elif self.is_gauge(metric) and len(self._sample_store[metric][tags]) >= 1:
            return self._sample_store[metric][tags][-1]

        else:
            raise UnknownValue()

    def get_sample(self, metric, tags=None):
        "Return the last value for that metric"
        x = self.get_sample_with_timestamp(metric, tags)
        assert type(x) == types.TupleType and len(x) == 3, x
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
                for t in self._sample_store[m]:
                    ts, val, hostname, device_name = self.get_sample_with_timestamp(m, t)
                    attributes = {}
                    if t:
                        attributes['tags'] = list(t)
                    if hostname:
                        attributes['host_name'] = hostname
                    if device_name:
                        attributes['device_name'] = device_name
                    metrics.append((m, int(ts), val, attributes))

            except:
                pass
        return metrics

def gethostname(agentConfig):
    if agentConfig.get("hostname") is not None:
        return agentConfig["hostname"]
    else:
        try:
            return socket.gethostname()
        except socket.error, e:
            logging.debug("processes: unable to get hostname: " + str(e))
