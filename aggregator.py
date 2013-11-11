import logging
from time import time
from checks.metric_types import MetricTypes

log = logging.getLogger(__name__)


# This is used to ensure that metrics with a timestamp older than
# RECENT_POINT_THRESHOLD_DEFAULT seconds (or the value passed in to
# the MetricsAggregator constructor) get discarded rather than being
# input into the incorrect bucket. Currently, the MetricsAggregator
# does not support submitting values for the past, and all values get
# submitted for the timestamp passed into the flush() function.
RECENT_POINT_THRESHOLD_DEFAULT = 30

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

    def flush(self, timestamp, interval):
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

    def flush(self, timestamp, interval):
        if self.value is not None:
            res = [self.formatter(
                metric=self.name,
                timestamp=timestamp,
                value=self.value,
                tags=self.tags,
                hostname=self.hostname,
                device_name=self.device_name,
                metric_type=MetricTypes.GAUGE,
            )]
            self.value = None
            return res

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

    def flush(self, timestamp, interval):
        try:
            value = self.value / interval
            return [self.formatter(
                metric=self.name,
                value=value,
                timestamp=timestamp,
                tags=self.tags,
                hostname=self.hostname,
                device_name=self.device_name,
                metric_type=MetricTypes.RATE,
            )]
        finally:
            self.value = 0


class Histogram(Metric):
    """ A metric to track the distribution of a set of values. """

    def __init__(self, formatter, name, tags, hostname, device_name):
        self.formatter = formatter
        self.name = name
        self.count = 0
        self.samples = []
        self.percentiles = [0.95]
        self.tags = tags
        self.hostname = hostname
        self.device_name = device_name

    def sample(self, value, sample_rate):
        self.count += int(1 / sample_rate)
        self.samples.append(value)
        self.last_sample_time = time()

    def flush(self, ts, interval):
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
            ('count', self.count/interval)
        ]

        metrics = [self.formatter(
                hostname=self.hostname,
                device_name=self.device_name,
                tags=self.tags,
                metric='%s.%s' % (self.name, suffix),
                value=value,
                timestamp=ts,
                metric_type=MetricTypes.GAUGE,
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
                timestamp=ts,
                metric_type=MetricTypes.GAUGE,
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

    def flush(self, timestamp, interval):
        if not self.values:
            return []
        try:
            return [self.formatter(
                hostname=self.hostname,
                device_name=self.device_name,
                tags=self.tags,
                metric=self.name,
                value=len(self.values),
                timestamp=timestamp,
                metric_type=MetricTypes.GAUGE,
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
            log.warn('Metric %s has an interval of 0. Not flushing.' % self.name)
            raise Infinity()

        delta = sample2[1] - sample1[1]
        if delta < 0:
            log.warn('Metric %s has a rate < 0. Not flushing.' % self.name)
            raise UnknownValue()

        return (delta / float(interval))

    def flush(self, timestamp, interval):
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
                timestamp=timestamp,
                metric_type=MetricTypes.GAUGE,
            )]
        finally:
            self.samples = self.samples[-1:]


class MetricsAggregator(object):
    """
    A metric aggregator class.
    """

    # Types of metrics that allow strings
    ALLOW_STRINGS = ['s', ]

    def __init__(self, hostname, interval=1.0, expiry_seconds=300, formatter=None, recent_point_threshold=None):
        self.metrics = {}
        self.events = []
        self.total_count = 0
        self.count = 0
        self.event_count = 0
        self.metric_type_to_class = {
            'g': Gauge,
            'c': Counter,
            'h': Histogram,
            'ms': Histogram,
            's': Set,
            '_dd-r': Rate,
        }
        self.hostname = hostname
        self.expiry_seconds = expiry_seconds
        self.formatter = formatter or api_formatter
        self.interval = float(interval)

        recent_point_threshold = recent_point_threshold or RECENT_POINT_THRESHOLD_DEFAULT
        self.recent_point_threshold = int(recent_point_threshold)
        self.num_discarded_old_points = 0

    def packets_per_second(self, interval):
        if interval == 0:
            return 0
        return round(float(self.count)/interval, 2)

    def parse_metric_packet(self, packet):
        name_and_metadata = packet.split(':', 1)

        if len(name_and_metadata) != 2:
            raise Exception('Unparseable metric packet: %s' % packet)

        name = name_and_metadata[0]
        metadata = name_and_metadata[1].split('|')

        if len(metadata) < 2:
            raise Exception('Unparseable metric packet: %s' % packet)

        # Submit the metric
        raw_value = metadata[0]
        metric_type = metadata[1]

        if metric_type in self.ALLOW_STRINGS:
            value = raw_value
        else:
            # Try to cast as an int first to avoid precision issues, then as a
            # float.
            try:
                value = int(raw_value)
            except ValueError:
                try:
                    value = float(raw_value)
                except ValueError:
                    # Otherwise, raise an error saying it must be a number
                    raise Exception('Metric value must be a number: %s, %s' % (name, raw_value))


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

        return name, value, metric_type, tags, sample_rate

    def _unescape_event_text(self, string):
        return string.replace('\\n', '\n')

    def parse_event_packet(self, packet):
        try:
            name_and_metadata = packet.split(':', 1)
            if len(name_and_metadata) != 2:
                raise Exception(u'Unparseable event packet: %s' % packet)
            # Event syntax:
            # _e{5,4}:title|body|meta
            name = name_and_metadata[0]
            metadata = unicode(name_and_metadata[1])
            title_length, text_length = name.split(',')
            title_length = int(title_length[3:])
            text_length = int(text_length[:-1])

            event = {
                'title': metadata[:title_length],
                'text': self._unescape_event_text(metadata[title_length+1:title_length+text_length+1])
            }
            meta = metadata[title_length+text_length+1:]
            for m in meta.split('|')[1:]:
                if m[0] == u't':
                    event['alert_type'] = m[2:]
                elif m[0] == u'k':
                    event['aggregation_key'] = m[2:]
                elif m[0] == u's':
                    event['source_type_name'] = m[2:]
                elif m[0] == u'd':
                    event['date_happened'] = int(m[2:])
                elif m[0] == u'p':
                    event['priority'] = m[2:]
                elif m[0] == u'h':
                    event['hostname'] = m[2:]
                elif m[0] == u'#':
                    event['tags'] = sorted(m[1:].split(u','))
            return event
        except IndexError, ValueError:
            raise Exception(u'Unparseable event packet: %s' % packet)

    def submit_packets(self, packets):
        for packet in packets.split("\n"):

            if not packet.strip():
                continue

            if packet.startswith('_e'):
                self.event_count += 1
                event = self.parse_event_packet(packet)
                self.event(**event)
            else:
                self.count += 1
                name, value, mtype, tags, sample_rate = self.parse_metric_packet(packet)
                self.submit_metric(name, value, mtype, tags=tags, sample_rate=sample_rate)

    def submit_metric(self, name, value, mtype, tags=None, hostname=None,
                                device_name=None, timestamp=None, sample_rate=1):
        # Avoid calling extra functions to dedupe tags if there are none
        if tags is None:
            context = (name, tuple(), hostname, device_name)
        else:
            context = (name, tuple(sorted(set(tags))), hostname, device_name)
        if context not in self.metrics:
            metric_class = self.metric_type_to_class[mtype]
            self.metrics[context] = metric_class(self.formatter, name, tags,
                hostname or self.hostname, device_name)
        cur_time = time()
        if timestamp is not None and cur_time - int(timestamp) > self.recent_point_threshold:
            self.num_discarded_old_points += 1
        else:
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

    def event(self, title, text, date_happened=None, alert_type=None, aggregation_key=None, source_type_name=None, priority=None, tags=None, hostname=None):
        event = {
            'title': title,
            'text': text,
        }
        if date_happened is not None:
            event['date_happened'] = date_happened
        else:
            event['date_happened'] = int(time())
        if alert_type is not None:
            event['alert_type'] = alert_type
        if aggregation_key is not None:
            event['aggregation_key'] = aggregation_key
        if source_type_name is not None:
            event['source_type_name'] = source_type_name
        if priority is not None:
            event['priority'] = priority
        if tags is not None:
            event['tags'] = sorted(tags)
        if hostname is not None:
            event['host'] = hostname
        else:
            event['host'] = self.hostname

        self.events.append(event)

    def flush(self):
        timestamp = time()
        expiry_timestamp = timestamp - self.expiry_seconds

        # Flush points and remove expired metrics. We mutate this dictionary
        # while iterating so don't use an iterator.
        metrics = []
        for context, metric in self.metrics.items():
            if metric.last_sample_time < expiry_timestamp:
                log.debug("%s hasn't been submitted in %ss. Expiring." % (context, self.expiry_seconds))
                del self.metrics[context]
            else:
                metrics += metric.flush(timestamp, self.interval)

        # Log a warning regarding metrics with old timestamps being submitted
        if self.num_discarded_old_points > 0:
            log.warn('%s points were discarded as a result of having an old timestamp' % self.num_discarded_old_points)
            self.num_discarded_old_points = 0

        # Save some stats.
        log.debug("received %s payloads since last flush" % self.count)
        self.total_count += self.count
        self.count = 0
        return metrics

    def flush_events(self):
        events = self.events
        self.events = []

        self.total_count += self.event_count
        self.event_count = 0

        log.debug("Received %d events since last flush" % len(events))

        return events

    def send_packet_count(self, metric_name):
        self.submit_metric(metric_name, self.count, 'g')


def api_formatter(metric, value, timestamp, tags, hostname, device_name=None, metric_type=None):
    # Workaround for a bug in minjson serialization
    # (https://github.com/DataDog/dd-agent/issues/422)
    if tags is not None and isinstance(tags, tuple) and len(tags) == 1:
        tags = list(tags)
    return {
        'metric': metric,
        'points': [(timestamp, value)],
        'tags': tags,
        'host': hostname,
        'device_name': device_name,
        'type': metric_type or MetricTypes.GAUGE,
    }
