# stdlib
from datetime import datetime
import glob
from itertools import groupby
import os
import re
import sys
import time
import traceback

# project
from checks import LaconicFilter
import modules
from util import windows_friendly_colon_split
from utils.tailfile import TailFile

def partition(s, sep):
    pos = s.find(sep)
    if pos == -1:
        return (s, sep, '')
    else:
        return s[0:pos], sep, s[pos + len(sep):]


def point_sorter(p):
    # Sort and group by timestamp, metric name, host_name, device_name
    return (p[1], p[0], p[3].get('host_name', None), p[3].get('device_name', None))


class EventDefaults(object):
    EVENT_TYPE = 'dogstream_event'
    EVENT_OBJECT = 'dogstream_event:default'


class Dogstreams(object):
    @classmethod
    def init(cls, logger, config):
        dogstreams_config = config.get('dogstreams', None)
        if dogstreams_config:
            dogstreams = cls._instantiate_dogstreams(logger, config, dogstreams_config)
        else:
            dogstreams = []

        logger.info("Dogstream parsers: %s" % repr(dogstreams))

        return cls(logger, dogstreams)

    def __init__(self, logger, dogstreams):
        self.logger = logger
        self.dogstreams = dogstreams

    @classmethod
    def _instantiate_dogstreams(cls, logger, config, dogstreams_config):
        """
        Expecting dogstreams config value to look like:
           <dogstream value>, <dog stream value>, ...
        Where <dogstream value> looks like:
           <log path>
        or
           <log path>:<module>:<parser function>
        """
        dogstreams = []
        # Create a Dogstream object for each <dogstream value>
        for config_item in dogstreams_config.split(','):
            try:
                config_item = config_item.strip()
                parts = windows_friendly_colon_split(config_item)

                if len(parts) == 2:
                    logger.warn("Invalid dogstream: %s" % ':'.join(parts))
                    continue

                log_path = cls._get_dogstream_log_paths(parts[0]) if len(parts) else []
                parser_spec = ':'.join(parts[1:3]) if len(parts) >= 3 else None
                parser_args = parts[3:] if len(parts) >= 3 else None

                for path in log_path:
                    dogstreams.append(Dogstream.init(
                        logger,
                        log_path=path,
                        parser_spec=parser_spec,
                        parser_args=parser_args,
                        config=config))
            except Exception:
                logger.exception("Cannot build dogstream")

        return dogstreams

    @classmethod
    def _get_dogstream_log_paths(cls, path):
        """
        Paths may include wildcard *'s and ?'s.
        """
        if '*' not in path:
            return [path]
        return glob.glob(path)

    def check(self, agentConfig, move_end=True):
        if not self.dogstreams:
            return {}

        output = {}
        for dogstream in self.dogstreams:
            try:
                result = dogstream.check(agentConfig, move_end)
                # result may contain {"dogstream": [new]}.
                # If output contains {"dogstream": [old]}, that old value will get concatenated with the new value
                assert type(result) == type(output), "dogstream.check must return a dictionary"
                for k in result:
                    if k in output:
                        output[k].extend(result[k])
                    else:
                        output[k] = result[k]
            except Exception:
                self.logger.exception("Error in parsing %s" % (dogstream.log_path))
        return output

class Dogstream(object):

    @classmethod
    def init(cls, logger, log_path, parser_spec=None, parser_args=None, config=None):
        class_based = False
        parse_func = None
        parse_args = tuple(parser_args or ())

        if parser_spec:
            try:
                parse_func = modules.load(parser_spec)
                if isinstance(parse_func, type):
                    logger.info('Instantiating class-based dogstream')
                    parse_func = parse_func(
                        user_args=parse_args or (),
                        logger=logger,
                        log_path=log_path,
                        config=config,
                    )
                    parse_args = ()
                    class_based = True
                else:
                    logger.info('Instantiating function-based dogstream')
            except Exception:
                logger.exception(traceback.format_exc())
                logger.error('Could not load Dogstream line parser "%s" PYTHONPATH=%s' % (
                    parser_spec,
                    os.environ.get('PYTHONPATH', ''))
                )
            logger.info("dogstream: parsing %s with %s (requested %s)" % (log_path, parse_func, parser_spec))
        else:
            logger.info("dogstream: parsing %s with default parser" % log_path)

        return cls(logger, log_path, parse_func, parse_args, class_based=class_based)

    def __init__(self, logger, log_path, parse_func=None, parse_args=(), class_based=False):
        self.logger = logger
        self.class_based = class_based

        # Apply LaconicFilter to avoid log flooding
        self.logger.addFilter(LaconicFilter("dogstream"))

        self.log_path = log_path
        self.parse_func = parse_func or self._default_line_parser
        self.parse_args = parse_args

        self._gen = None
        self._values = None
        self._freq = 15 # Will get updated on each check()
        self._error_count = 0L
        self._line_count = 0L
        self.parser_state = {}

    def check(self, agentConfig, move_end=True):
        if self.log_path:
            self._freq = int(agentConfig.get('check_freq', 15))
            self._values = []
            self._events = []

            # Build our tail -f
            if self._gen is None:
                self._gen = TailFile(self.logger, self.log_path, self._line_parser).tail(line_by_line=False, move_end=move_end)

            # read until the end of file
            try:
                self._gen.next()
                self.logger.debug("Done dogstream check for file {0}".format(self.log_path))
                self.logger.debug("Found {0} metric points".format(len(self._values)))
            except StopIteration, e:
                self.logger.exception(e)
                self.logger.warn("Can't tail %s file" % self.log_path)

            check_output = self._aggregate(self._values)
            if self._events:
                check_output.update({"dogstreamEvents": self._events})
                self.logger.debug("Found {0} events".format(len(self._events)))
            return check_output
        else:
            return {}

    def _line_parser(self, line):
        try:
            # alq - Allow parser state to be kept between invocations
            # This means a new argument can be passed the custom parsing function
            # to store context that can be shared between parsing of lines.
            # One example is a running counter, which is incremented each time
            # a line is processed.
            parsed = None
            if self.class_based:
                parsed = self.parse_func.parse_line(line)
            else:
                try:
                    parsed = self.parse_func(self.logger, line, self.parser_state, *self.parse_args)
                except TypeError:
                    # Arity of parse_func is 3 (old-style), not 4
                    parsed = self.parse_func(self.logger, line)

            self._line_count += 1

            if parsed is None:
                return

            if isinstance(parsed, (tuple, dict)):
                parsed = [parsed]

            for datum in parsed:
                # Check if it's an event
                if isinstance(datum, dict):
                    # An event requires at least a title or a body
                    if 'msg_title' not in datum and 'msg_text' not in datum:
                        continue

                    # Populate the default fields
                    if 'event_type' not in datum:
                        datum['event_type'] = EventDefaults.EVENT_TYPE
                    if 'timestamp' not in datum:
                        datum['timestamp'] = time.time()
                    # Make sure event_object and aggregation_key (synonyms) are set
                    # FIXME when the backend treats those as true synonyms, we can
                    # deprecate event_object.
                    if 'event_object' in datum or 'aggregation_key' in datum:
                        datum['aggregation_key'] = datum.get('event_object', datum.get('aggregation_key'))
                    else:
                        datum['aggregation_key'] = EventDefaults.EVENT_OBJECT
                    datum['event_object'] = datum['aggregation_key']

                    self._events.append(datum)
                    continue

                # Otherwise, assume it's a metric
                try:
                    metric, ts, value, attrs = datum
                except Exception:
                    continue

                # Validation
                invalid_reasons = []
                try:
                    # Bucket points into 15 second buckets
                    ts = (int(float(ts)) / self._freq) * self._freq
                    date = datetime.fromtimestamp(ts)
                    assert date.year > 1990
                except Exception:
                    invalid_reasons.append('invalid timestamp')

                try:
                    value = float(value)
                except Exception:
                    invalid_reasons.append('invalid metric value')

                if invalid_reasons:
                    self.logger.debug('Invalid parsed values %s (%s): "%s"',
                        repr(datum), ', '.join(invalid_reasons), line)
                else:
                    self._values.append((metric, ts, value, attrs))
        except Exception:
            self.logger.debug("Error while parsing line %s" % line, exc_info=True)
            self._error_count += 1
            self.logger.error("Parser error: %s out of %s" % (self._error_count, self._line_count))

    def _default_line_parser(self, logger, line):
        sep = ' '
        metric, _, line = partition(line.strip(), sep)
        timestamp, _, line = partition(line.strip(), sep)
        value, _, line = partition(line.strip(), sep)

        attributes = {}
        try:
            while line:
                keyval, _, line = partition(line.strip(), sep)
                key, val = keyval.split('=', 1)
                attributes[key] = val
        except Exception:
            logger.debug(traceback.format_exc())

        return metric, timestamp, value, attributes

    def _aggregate(self, values):
        """ Aggregate values down to the second and store as:
            {
                "dogstream": [(metric, timestamp, value, {key: val})]
            }
            If there are many values per second for a metric, take the median
        """
        output = []

        values.sort(key=point_sorter)

        for (timestamp, metric, host_name, device_name), val_attrs in groupby(values, key=point_sorter):
            attributes = {}
            vals = []
            for _metric, _timestamp, v, a in val_attrs:
                try:
                    v = float(v)
                    vals.append(v)
                    attributes.update(a)
                except Exception:
                    self.logger.debug("Could not convert %s into a float", v)

            if len(vals) == 1:
                val = vals[0]
            elif len(vals) > 1:
                val = vals[-1]
            else: # len(vals) == 0
                continue

            metric_type = str(attributes.get('metric_type', '')).lower()
            if metric_type == 'gauge':
                val = float(val)
            elif metric_type == 'counter':
                val = sum(vals)

            output.append((metric, timestamp, val, attributes))

        if output:
            return {"dogstream": output}
        else:
            return {}


# Allow a smooth uninstall of previous version
class RollupLP:
    pass


class DdForwarder(object):

    QUEUE_SIZE = "queue_size"
    QUEUE_COUNT = "queue_count"

    RE_QUEUE_STAT = re.compile(r"\[.*\] Queue size: at (.*), (\d+) transaction\(s\), (\d+) KB")

    def __init__(self, logger, config):
        self.log_path = config.get('ddforwarder_log', '/var/log/ddforwarder.log')
        self.logger = logger
        self._gen = None

    def _init_metrics(self):
        self.metrics = {}

    def _add_metric(self, name, value, ts):

        if name in self.metrics:
            self.metrics[name].append((ts, value))
        else:
            self.metrics[name] = [(ts, value)]

    def _parse_line(self, line):

        try:
            m = self.RE_QUEUE_STAT.match(line)
            if m is not None:
                ts, count, size = m.groups()
                self._add_metric(self.QUEUE_SIZE, size, round(float(ts)))
                self._add_metric(self.QUEUE_COUNT, count, round(float(ts)))
        except Exception, e:
            self.logger.exception(e)

    def check(self, agentConfig, move_end=True):

        if self.log_path and os.path.isfile(self.log_path):

            #reset metric points
            self._init_metrics()

            # Build our tail -f
            if self._gen is None:
                self._gen = TailFile(self.logger, self.log_path, self._parse_line).tail(line_by_line=False,
                    move_end=move_end)

            # read until the end of file
            try:
                self._gen.next()
                self.logger.debug("Done ddforwarder check for file %s" % self.log_path)
            except StopIteration, e:
                self.logger.exception(e)
                self.logger.warn("Can't tail %s file" % self.log_path)

            return {'ddforwarder': self.metrics}
        else:
            self.logger.debug("Can't tail datadog forwarder log file: %s" % self.log_path)
            return {}


def testddForwarder():
    import logging

    logger = logging.getLogger("ddagent.checks.datadog")
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.StreamHandler())

    config = {'api_key':'my_apikey', 'ddforwarder_log': sys.argv[1]}
    dd = DdForwarder(logger, config)
    m = dd.check(config, move_end=False)
    while True:
        print m
        time.sleep(5)
        m = dd.check(config)


if __name__ == '__main__':
    testddForwarder()
