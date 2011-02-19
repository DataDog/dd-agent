'''
    Datadog agent

    Licensed under Simplified BSD License (see LICENSE)
    (C) Boxed Ice 2010 all rights reserved
    (C) Datadog, Inc 2011 All Rights Reserved
'''

import time
import types

from checks.nagios import Nagios
from checks.build import Hudson
from checks.db import CouchDb, MongoDb, MySql, Redis
from checks.queue import RabbitMq
from checks.system import Disk, IO, Load, Memory, Network, Processes, Cpu
from checks.web import Apache, Nginx
from checks.ganglia import Ganglia
from checks.datadog import RollupLP as ddRollupLP
from checks.cassandra import Cassandra
from checks.common import checks

# Konstants
class CheckException(Exception): pass
class Infinity(CheckException): pass
class NaN(CheckException): pass
class UnknownValue(CheckException): pass

class Check(object):
    """
    (Abstract) class for all checks with the ability to:
    * compute rates for counters
    """
    def __init__(self):
        # where to store samples, indexed by metric_name
        # metric_name: [(ts, value), (ts, value)]
        self._sample_store = {}
        self._counters = {} # metric_name: bool

    def counter(self, metric_name):
        """
        Treats the metric as a counter, i.e. computes its per second derivative
        """
        self._counters[metric_name] = True

    def is_counter(self, metric_name):
        "Is this metric a counter?"
        return metric_name in self._counters

    def gauge(self, metric_name):
        """
        Treats the metric as a guage, i.e. keep the data as is
        """
        pass

    def is_gauge(self, metric_name):
        return not self.is_counter(metric_name)

    def save_sample(self, metric_name, value, timestamp=None):
        """Save a simple sample, evict old values if needed"""
        if timestamp is None:
            timestamp = time.time()
        if metric_name not in self._sample_store:
            self._sample_store[metric_name] = []

        # Data eviction rules
        if self.is_gauge(metric_name):
            self._sample_store[metric_name] = [(timestamp, value)]
        elif self.is_counter(metric_name):
            if len(self._sample_store[metric_name]) == 0:
                self._sample_store[metric_name] = [(timestamp, value)]
            else:
                self._sample_store[metric_name] = self._sample_store[metric_name][-1:] + [(timestamp, value)]
        else:
            raise CheckException("%s must be either gauge or counter, skipping sample at %s" % (metric_name, time.ctime(timestamp)))

        if self.is_gauge(metric_name):
            assert len(self._sample_store[metric_name]) in (0, 1), self._sample_store[metric_name]
        elif self.is_counter(metric_name):
            assert len(self._sample_store[metric_name]) in (0, 1, 2), self._sample_store[metric_name]

    def save_samples(self, pairs_or_triplets):
        pass
    
    @classmethod
    def _rate(cls, sample1, sample2):
        "Simple rate"
        try:
            interval = sample2[0] - sample1[0]
            if interval == 0:
                raise Infinity()
            delta = sample2[1] - sample1[1]
            return (sample2[0], delta / interval)
        except Infinity:
            raise
        except Exception, e:
            raise NaN(e)

    def get_sample_with_timestamp(self, metric_name):
        "Get (timestamp-epoch-style, value)"
        if metric_name not in self._sample_store:
            raise UnknownValue()
        elif self.is_counter(metric_name) and len(self._sample_store[metric_name]) < 2:
            raise UnknownValue()
        elif self.is_counter(metric_name) and len(self._sample_store[metric_name]) >= 2:
            return self._rate(self._sample_store[metric_name][-2], self._sample_store[metric_name][-1])
        elif self.is_gauge(metric_name) and len(self._sample_store[metric_name]) >= 1:
            return self._sample_store[metric_name][-1]
        else:
            raise UnknownValue()

    def get_sample(self, metric_name):
        "Return the last value for that metric_name"
        x = self.get_sample_with_timestamp(metric_name)
        assert type(x) == types.TupleType and len(x) == 2, x
        return x[1]
        
    def get_samples(self):
        "Return all values"
        values = []
        for m in self._metric_store:
            values.append(self.get_sample(m))
        return values

    def get_samples_with_timestamps(self):
        pass
