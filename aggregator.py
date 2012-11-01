import logging
from time import time

logger = logging.getLogger(__name__)


class Infinity(Exception): pass
class UnknownValue(Exception): pass

class Metric(object):
    """
    A base metric class that accepts points, slices them into time intervals
    and performs roll-ups within those intervals.
    """

    def sample(self, value, sample_rate):
        """ Add a point to the given metric. """
        raise NotImplementedError()

    def flush(self, timestamp):
        """ Flush all metrics up to the given timestamp. """
        raise NotImplementedError()

class Gauge(Metric):
    """ A metric that tracks a value at particular points in time. """

    def __init__(self, formatter, name, tags, hostname, device_name):
        self.formatter = formatter
        self.name = name
        self.value = None
        self.tags = tags
        self.hostname = hostname
        self.device_name = device_name
        self.last_sample_time = None

    def sample(self, value, sample_rate):
        self.value = value
        self.last_sample_time = time()

    def flush(self, timestamp):
        if self.value is not None:
            return [self.formatter(
                metric=self.name,
                timestamp=timestamp,
                value=self.value,
                tags=self.tags,
                hostname=self.hostname,
                device_name=self.device_name
            )]
            self.value = None

        return []

class Counter(Metric):
    """ A metric that tracks a counter value. """

    def __init__(self, formatter, name, tags, hostname, device_name):
        self.formatter = formatter
        self.name = name
        self.value = 0
        self.tags = tags
        self.hostname = hostname
        self.device_name = device_name

    def sample(self, value, sample_rate):
        self.value += value * int(1 / sample_rate)
        self.last_sample_time = time()

    def flush(self, timestamp):
        try:
            return [self.formatter(
                metric=self.name,
                value=self.value,
                timestamp=timestamp,
                tags=self.tags,
                hostname=self.hostname,
                device_name=self.device_name
            )]
        finally:
            self.value = 0


class Histogram(Metric):
    """ A metric to track the distribution of a set of values. """

    def __init__(self, formatter, name, tags, hostname, device_name):
        self.formatter = formatter
        self.name = name
        self.max = float("-inf")
        self.min = float("inf")
        self.sum = 0
        self.count = 0
        self.sample_size = 1000
        self.samples = []
        self.percentiles = [0.95]
        self.tags = tags
        self.hostname = hostname
        self.device_name = device_name

    def sample(self, value, sample_rate):
        self.count += int(1 / sample_rate)
        self.samples.append(value)
        self.last_sample_time = time()

    def flush(self, ts):
        if not self.count:
            return []

        self.samples.sort()
        length = len(self.samples)

        max_ = self.samples[-1]
        med = self.samples[int(round(length/2 - 1))]
        avg = sum(self.samples) / float(length)

        metric_aggrs = [
            ('max', max_),
            ('median', med),
            ('avg', avg),
            ('count', self.count)
        ]

        metrics = [self.formatter(
                hostname=self.hostname,
                device_name=self.device_name,
                tags=self.tags,
                metric='%s.%s' % (self.name, suffix),
                value=value,
                timestamp=ts
            ) for suffix, value in metric_aggrs
        ]

        for p in self.percentiles:
            val = self.samples[int(round(p * length - 1))]
            name = '%s.%spercentile' % (self.name, int(p * 100))
            metrics.append(self.formatter(
                hostname=self.hostname,
                tags=self.tags,
                metric=name,
                value=val,
                timestamp=ts
            ))

        # Reset our state.
        self.samples = []
        self.count = 0

        return metrics


class Set(Metric):
    """ A metric to track the number of unique elements in a set. """

    def __init__(self, formatter, name, tags, hostname, device_name):
        self.formatter = formatter
        self.name = name
        self.tags = tags
        self.hostname = hostname
        self.device_name = device_name
        self.values = set()

    def sample(self, value, sample_rate):
        self.values.add(value)
        self.last_sample_time = time()

    def flush(self, timestamp):
        if not self.values:
            return []
        try:
            return [self.formatter(
                hostname=self.hostname,
                device_name=self.device_name,
                tags=self.tags,
                metric=self.name,
                value=len(self.values),
                timestamp=timestamp
            )]
        finally:
            self.values = set()


class Rate(Metric):
    """ Track the rate of metrics over each flush interval """

    def __init__(self, formatter, name, tags, hostname, device_name):
        self.formatter = formatter
        self.name = name
        self.tags = tags
        self.hostname = hostname
        self.device_name = device_name
        self.samples = []

    def sample(self, value, sample_rate):
        ts = time()
        self.samples.append((int(ts), value))
        self.last_sample_time = ts

    def _rate(self, sample1, sample2):
        interval = sample2[0] - sample1[0]
        if interval == 0:
            logger.warn('Metric %s has an interval of 0. Not flushing.' % self.name)
            raise Infinity()

        delta = sample2[1] - sample1[1]
        if delta < 0:
            logger.warn('Metric %s has a rate < 0. Not flushing.' % self.name)
            raise UnknownValue()

        return (delta / interval)

    def flush(self, timestamp):
        if len(self.samples) < 2:
            return []
        try:
            try:
                val = self._rate(self.samples[-2], self.samples[-1])
            except:
                return []

            return [self.formatter(
                hostname=self.hostname,
                device_name=self.device_name,
                tags=self.tags,
                metric=self.name,
                value=val,
                timestamp=timestamp
            )]
        finally:
            self.samples = self.samples[-1:]



class MetricsAggregator(object):
    """
    A metric aggregator class.
    """

    def __init__(self, hostname, expiry_seconds=300, formatter=None):
        self.metrics = {}
        self.total_count = 0
        self.count = 0
        self.metric_type_to_class = {
            'g': Gauge,
            'c': Counter,
            'h': Histogram,
            'ms' : Histogram,
            's'  : Set,
            '_dd-r': Rate,
        }
        self.hostname = hostname
        self.expiry_seconds = expiry_seconds
        self.formatter = formatter or self.api_formatter

    def submit_packets(self, packets):
        from util import cast_metric_val

        for packet in packets.split("\n"):
            self.count += 1
            # We can have colons in tags, so split once.
            name_and_metadata = packet.split(':', 1)

            if not packet.strip():
                continue

            if len(name_and_metadata) != 2:
                raise Exception('Unparseable packet: %s' % packet)

            name = name_and_metadata[0]
            metadata = name_and_metadata[1].split('|')

            if len(metadata) < 2:
                raise Exception('Unparseable packet: %s' % packet)

            try:
                value = cast_metric_val(metadata[0])
            except ValueError:
                raise Exception('Metric value must be a number: %s, %s' % name, metadata[0])

            # Parse the optional values - sample rate & tags.
            sample_rate = 1
            tags = None
            for m in metadata[2:]:
                # Parse the sample rate
                if m[0] == '@':
                    sample_rate = float(m[1:])
                    assert 0 <= sample_rate <= 1
                elif m[0] == '#':
                    tags = tuple(sorted(m[1:].split(',')))

            # Submit the metric
            mtype = metadata[1]
            self.submit_metric(name, value, mtype, tags=tags, sample_rate=sample_rate)

    def submit_metric(self, name, value, mtype, tags=None, hostname=None,
      device_name=None, timestamp=None, sample_rate=1):
        context = (name, tuple(tags or []), hostname, device_name)
        if context not in self.metrics:
            metric_class = self.metric_type_to_class[mtype]
            self.metrics[context] = metric_class(self.formatter, name, tags,
                hostname or self.hostname, device_name)
        self.metrics[context].sample(value, sample_rate)

    def gauge(self, name, value, tags=None, hostname=None, device_name=None, timestamp=None):
        self.submit_metric(name, value, 'g', tags, hostname, device_name, timestamp)

    def increment(self, name, value=1, tags=None, hostname=None, device_name=None):
        self.submit_metric(name, value, 'c', tags, hostname, device_name)

    def decrement(self, name, value=-1, tags=None, hostname=None, device_name=None):
        self.submit_metric(name, value, 'c', tags, hostname, device_name)

    def rate(self, name, value, tags=None, hostname=None, device_name=None):
        self.submit_metric(name, value, '_dd-r', tags, hostname, device_name)

    def histogram(self, name, value, tags=None, hostname=None, device_name=None):
        self.submit_metric(name, value, 'h', tags, hostname, device_name)

    def set(self, name, value, tags=None, hostname=None, device_name=None):
        self.submit_metric(name, value, 's', tags, hostname, device_name)

    def flush(self):
        timestamp = time()
        expiry_timestamp = timestamp - self.expiry_seconds

        # Flush points and remove expired metrics. We mutate this dictionary
        # while iterating so don't use an iterator.
        metrics = []
        for context, metric in self.metrics.items():
            if metric.last_sample_time < expiry_timestamp:
                logger.debug("%s hasn't been submitted in %ss. Expiring." % (context, self.expiry_seconds))
                del self.metrics[context]
            else:
                metrics += metric.flush(timestamp)

        # Save some stats.
        logger.debug("received %s payloads since last flush" % self.count)
        self.total_count += self.count
        self.count = 0
        return metrics

    def send_packet_count(self, metric_name):
        self.submit_metric(metric_name, self.count, 'g')

    def api_formatter(self, metric, value, timestamp, tags, hostname, device_name=None):
        return {
            'metric' : metric,
            'points' : [(timestamp, value)],
            'tags' : tags,
            'host' : hostname,
            'device_name': device_name
        }
