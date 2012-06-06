"""
Aggregates different types of metrics.
"""


import logging
import random
import time


logger = logging.getLogger('dogstatsd')


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

    def __init__(self, name, tags):
        self.name = name
        self.value = None
        self.tags = tags

    def sample(self, value, sample_rate):
        self.value = value

    def flush(self, timestamp):
        return [{
            'metric' : self.name,
            'points' : [(timestamp, self.value)],
            'tags' : self.tags
        }]


class Counter(Metric):
    """ A metric that tracks a counter value. """

    def __init__(self, name, tags):
        self.name = name
        self.value = 0
        self.tags = tags

    def sample(self, value, sample_rate):
        self.value += value * int(1 / sample_rate)

    def flush(self, timestamp):
        return [{
            'metric' : self.name,
            'points' : [(timestamp, self.value)],
            'tags' : self.tags
        }]


class Histogram(Metric):
    """ A metric to track the distribution of a set of values. """

    def __init__(self, name, tags):
        self.name = name
        self.max = float("-inf")
        self.min = float("inf")
        self.sum = 0
        self.count = 0
        self.sample_size = 1000
        self.samples = []
        self.percentiles = [0.75, 0.85, 0.95, 0.99]
        self.tags = tags

    def sample(self, value, sample_rate):
        count = int(1 / sample_rate)
        self.max = self.max if self.max > value else value
        self.min = self.min if self.min < value else value
        self.sum += value * count
        # Is there a cleaner way to do this?
        for i in xrange(count):
            if self.count < self.sample_size:
                self.samples.append(value)
            else:
                self.samples[random.randrange(0, self.sample_size)] = value
        self.count += count

    def flush(self, ts):
        if not self.count:
            return []

        metrics = [
            {'tags': self.tags, 'metric' : '%s.min' % self.name, 'points' : [(ts, self.min)]},
            {'tags': self.tags, 'metric' : '%s.max' % self.name, 'points' : [(ts, self.max)]},
            {'tags': self.tags, 'metric' : '%s.avg' % self.name, 'points' : [(ts, self.average())]},
            {'tags': self.tags, 'metric' : '%s.count' % self.name, 'points' : [(ts, self.count)]},
        ]

        length = len(self.samples)
        self.samples.sort()
        for p in self.percentiles:
            val = self.samples[int(round(p * length - 1))]
            name = '%s.%spercentile' % (self.name, int(p * 100))
            metrics.append({'tags':self.tags, 'metric': name, 'points': [(ts, val)]})
        return metrics

    def average(self):
        return float(self.sum) / self.count



class MetricsAggregator(object):
    """
    A metric aggregator class.
    """

    def __init__(self):
        self.metrics = {}
        self.count = 0
        self.metric_type_to_class = {
            'g': Gauge,
            'c': Counter,
            'h': Histogram,
            'ms' : Histogram
        }

    def submit(self, packet):
        self.count += 1
        # We can have colons in tags, so split once.
        name_and_metadata = packet.split(':', 1)

        if len(name_and_metadata) != 2:
            raise Exception('Unparseable packet: %s' % packet)

        name = name_and_metadata[0]
        metadata = name_and_metadata[1].split('|')

        if len(metadata) < 2:
            raise Exception('Unparseable packet: %s' % packet)

        # Get the value & type of the metric.
        value = float(metadata[0])
        type_ = metadata[1]

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

        context = (name, tags)

        if context not in self.metrics:
            metric_class = self.metric_type_to_class[type_]
            self.metrics[context] = metric_class(name, tags)
        self.metrics[context].sample(value, sample_rate)


    def flush(self, timestamp=None):
        timestamp = timestamp or time.time()
        metrics = []
        for context, metric in self.metrics.items():
            metrics += metric.flush(timestamp)
            del self.metrics[context]
        logger.info("received %s payloads since last flush" % self.count)
        self.count = 0
        return metrics
