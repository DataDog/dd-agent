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

    def __init__(self, formatter, name, tags, hostname):
        self.formatter = formatter
        self.name = name
        self.value = None
        self.tags = tags
        self.hostname = hostname
        self.last_sample_time = None

    def sample(self, value, sample_rate):
        self.value = value
        self.last_sample_time = time()

    def flush(self, timestamp):
        # Gauges don't reset. Continue to send the same value.
        return [self.formatter(
            metric=self.name,
            timestamp=timestamp,
            value=self.value,
            tags=self.tags,
            hostname=self.hostname
        )]


class Counter(Metric):
    """ A metric that tracks a counter value. """

    def __init__(self, formatter, name, tags, hostname):
        self.formatter = formatter
        self.name = name
        self.value = 0
        self.tags = tags
        self.hostname = hostname

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
                hostname=self.hostname
            )]
        finally:
            self.value = 0


class Histogram(Metric):
    """ A metric to track the distribution of a set of values. """

    def __init__(self, formatter, name, tags, hostname):
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
        avg = sum(self.samples)/length

        metrics = [
            self.formatter(host=self.hostname, tags=self.tags, metric='%s.max' % self.name, value=max, timestamp=ts),
            self.formatter(host=self.hostname, tags=self.tags, metric='%s.median' % self.name, value=med, timestamp=ts),
            self.formatter(host=self.hostname, tags=self.tags, metric='%s.avg' % self.name, value=avg, timestamp=ts),
            self.formatter(host=self.hostname, tags=self.tags, metric='%s.count' % self.name, value=self.count, timestamp=ts),
        ]

        for p in self.percentiles:
            val = self.samples[int(round(p * length - 1))]
            name = '%s.%spercentile' % (self.name, int(p * 100))
            metrics.append(self.formatter(
                host=self.hostname,
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

    def __init__(self, name, tags, hostname):
        self.name = name
        self.tags = tags
        self.hostname = hostname
        self.values = set()

    def sample(self, value, sample_rate):
        self.values.add(value)
        self.last_sample_time = time()

    def flush(self, timestamp):
        if not self.values:
            return []
        try:
            return [{
                'metric' : self.name,
                'points' : [(timestamp, len(self.values))],
                'tags' : self.tags,
                'host' : self.hostname
            }]
        finally:
            self.values = set()



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
        }
        self.hostname = hostname
        self.expiry_seconds = expiry_seconds
        self.formatter = formatter or self.api_formatter

    def submit(self, packet, hostname=None, device_name=None):
        for packet in packets.split("\n"):
            self.count += 1
            # We can have colons in tags, so split once.
            name_and_metadata = packet.split(':', 1)

            if len(name_and_metadata) != 2:
                raise Exception('Unparseable packet: %s' % packet)

            name = name_and_metadata[0]
            metadata = name_and_metadata[1].split('|')

            if len(metadata) < 2:
                raise Exception('Unparseable packet: %s' % packet)

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
                metric_class = self.metric_type_to_class[metadata[1]]
                self.metrics[context] = metric_class(name, tags, self.hostname)
            self.metrics[context].sample(float(metadata[0]), sample_rate)

    def gauge(metric, value, tags=None, hostname=None, device_name=None):
        ''' Format the gague metric into a StatsD packet format and submit'''
        packet = self._create_packet(metric, value, tags, 'g')
        self.submit(packet, hostname=hostname, device_name=device_name)

    def increment(metric, value, tags=None, hostname=None, device_name=None):
        ''' Format the counter metric into a StatsD packet format and submit'''
        packet = self._create_packet(metric, value, tags, 'c')
        self.submit(packet, hostname=hostname, device_name=device_name)

    def histogram(metric, value, tags=None, hostname=None, device_name=None):
        ''' Format the histogram metric into a StatsD packet format and submit'''
        packet = self._create_packet(metric, value, tags, 'h')
        self.submit(packet, hostname=hostname, device_name=device_name)

    def _create_packet(metric, value, tags, stat_type):
        packet = '%s:%s|%s' % (metric, value, stat_type)
        if tags:
            packet += '|#%s' % ','.join(tags)
        return packet

    def flush(self, include_diagnostic_stats=True):

        timestamp = time()
        expiry_timestamp = timestamp - self.expiry_seconds

        # Flush points and remove expired metrics. We mutate this dictionary
        # while iterating so don't use an iterator.
        metrics = []
        for context, metric in self.metrics.items():
            if metric.last_sample_time < expiry_timestamp:
                logger.info("%s hasnt been submitted in %ss. Expiring." % (context, self.expiry_seconds))
                del self.metrics[context]
            else:
                metrics += metric.flush(timestamp)

        # Track how many points we see.
        if include_diagnostic_stats:
            metrics.append(self.formatter(
                host=self.hostname,
                tags=None,
                metric=datadog.dogstatsd.packet.count,
                timestamp=timestamp,
                val=self.count
            ))

        # Save some stats.
        logger.info("received %s payloads since last flush" % self.count)
        self.total_count += self.count
        self.count = 0
        return metrics

    def api_formatter(self, metric, value, timestamp, tags, hostname, device_name):
        return {
            'metric' : metric,
            'points' : [(timestamp, value)],
            'tags' : tags,
            'host' : hostname,
            'device_name': device_name
        }
