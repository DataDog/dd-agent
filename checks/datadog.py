from checks.utils import TailFile
import modules
import os
import sys
import traceback
import re
import time
from datetime import datetime
from itertools import groupby # >= python 2.4

from checks import LaconicFilter

if hasattr('some string', 'partition'):
    def partition(s, sep):
        return s.partition(sep)
else:
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
    EVENT_TYPE   = 'dogstream_event'
    EVENT_OBJECT = 'dogstream_event:default'

class Dogstreams(object):
    @classmethod
    def init(cls, logger, config):
        dogstreams_config = config.get('dogstreams', None)
        dogstreams = []
        if dogstreams_config:
            # Expecting dogstreams config value to look like:
            #   <dogstream value>, <dog stream value>, ...
            # Where <dogstream value> looks like:
            #   <log path> 
            # or 
            #   <log path>:<module>:<parser function>

            # Create a Dogstream object for each <dogstream value>
            for config_item in dogstreams_config.split(','):
                try:
                    config_item = config_item.strip()
                    parts = config_item.split(':')
                    if len(parts) == 1:
                        dogstreams.append(Dogstream.init(logger, log_path=parts[0]))
                    elif len(parts) == 2:
                        logger.warn("Invalid dogstream: %s" % ':'.join(parts))
                    elif len(parts) == 3:
                        dogstreams.append(Dogstream.init(logger, log_path=parts[0], parser_spec=':'.join(parts[1:])))
                    elif len(parts) > 3:
                        logger.warn("Invalid dogstream: %s" % ':'.join(parts))
                except:
                    logger.exception("Cannot build dogstream")
        
        perfdata_parsers = NagiosPerfData.init(logger, config)
        if perfdata_parsers:
            dogstreams.extend(perfdata_parsers)
        
        logger.info("Dogstream parsers: %s" % repr(dogstreams))

        return cls(logger, dogstreams)
    
    def __init__(self, logger, dogstreams):
        self.logger = logger

        self.dogstreams = dogstreams
    
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
            except:
                self.logger.exception("Error in parsing %s" % (dogstream.log_path))
        return output

class Dogstream(object):

    @classmethod
    def init(cls, logger, log_path, parser_spec=None):
        parse_func = None
        
        if parser_spec:
            try:
                parse_func = modules.load(parser_spec, 'parser')
            except:
                logger.exception(traceback.format_exc())
                logger.error('Could not load Dogstream line parser "%s" PYTHONPATH=%s' % (
                    parser_spec, 
                    os.environ.get('PYTHONPATH', ''))
                )
            logger.info("dogstream: parsing %s with %s (requested %s)" % (log_path, parse_func, parser_spec))
        else:
            logger.info("dogstream: parsing %s with default parser" % log_path)
        
        return cls(logger, log_path, parse_func)
    
    def __init__(self, logger, log_path, parse_func=None):
        self.logger = logger

        # Apply LaconicFilter to avoid log flooding
        self.logger.addFilter(LaconicFilter("dogstream"))
        
        self.log_path = log_path
        self.parse_func = parse_func or self._default_line_parser
        
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
                self.logger.debug("Done dogstream check for file %s, found %s metric points" % (self.log_path, len(self._values)))
            except StopIteration, e:
                self.logger.exception(e)
                self.logger.warn("Can't tail %s file" % self.log_path)
            
            check_output = self._aggregate(self._values)
            if self._events:
                check_output.update({"dogstreamEvents": self._events})
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
            try:
                parsed = self.parse_func(self.logger, line, self.parser_state)
            except TypeError, e:
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
                    if 'event_object' not in datum and 'aggregation_key' not in datum:
                        datum['aggregation_key'] = EventDefaults.EVENT_OBJECT
                    else:
                        datum['aggregation_key'] = datum.get('event_object', datum.get('aggregation_key'))
                    datum['event_object'] = datum['aggregation_key']
                    
                    self._events.append(datum)
                    continue

                # Otherwise, assume it's a metric
                try:
                    metric, ts, value, attrs = datum
                except:
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
        except Exception, e:
            self.logger.debug("Error while parsing line %s" % line)
            self._error_count += 1
            self.logger.error("Parser error: %s out of %s" % (self._error_count, self._line_count))
    
    def _default_line_parser(self, logger, line):
        original_line = line
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
        except Exception, e:
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
                except:
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
                val = int(val)            
            
            output.append((metric, timestamp, val, attributes))
        
        if output:
            return {"dogstream": output}
        else:
            return {}

class InvalidDataTemplate(Exception): pass

class NagiosPerfData(object):
    perfdata_field = '' # Should be overriden by subclasses
    metric_prefix = 'nagios'
    pair_pattern = re.compile(r"".join([
            r"'?(?P<label>[^=']+)'?=", 
            r"(?P<value>[-0-9.]+)", 
            r"(?P<unit>s|us|ms|%|B|KB|MB|GB|TB|c)?", 
            r"(;(?P<warn>@?[-0-9.~]*:?[-0-9.~]*))?", 
            r"(;(?P<crit>@?[-0-9.~]*:?[-0-9.~]*))?", 
            r"(;(?P<min>[-0-9.]*))?", 
            r"(;(?P<max>[-0-9.]*))?",
        ]))

    @classmethod
    def init(cls, logger, config):
        nagios_perf_config = config.get('nagios_perf_cfg', None)
        parsers = []
        if nagios_perf_config:
            nagios_config = cls.parse_nagios_config(nagios_perf_config)

            host_parser = NagiosHostPerfData.init(logger, nagios_config)
            if host_parser:
                parsers.append(host_parser)
            
            service_parser = NagiosServicePerfData.init(logger, nagios_config)            
            if service_parser:
                parsers.append(service_parser)
            
        return parsers
    
    @staticmethod
    def template_regex(file_template):
        try:
            # Escape characters that will be interpreted as regex bits
            # e.g. [ and ] in "[SERVICEPERFDATA]"
            regex = re.sub(r'[[\]*]', r'.', file_template)
            regex = re.sub(r'\$([^\$]*)\$', r'(?P<\1>[^\$]*)', regex)
            return re.compile(regex)
        except Exception, e:
            raise InvalidDataTemplate("%s (%s)"% (file_template, e))

    
    @staticmethod
    def underscorize(s):
        return s.replace(' ', '_').lower()

    @classmethod
    def parse_nagios_config(cls, filename):
        output = {}
        keys = [
            'host_perfdata_file_template',
            'service_perfdata_file_template',
            'host_perfdata_file',
            'service_perfdata_file',
        ]

        try:
            f = open(filename)
            for line in f:
                line = line.strip()
                if not line:
                    continue
                for key in keys:
                    if line.startswith(key + '='):
                        eq_pos = line.find('=')
                        if eq_pos:
                            output[key] = line[eq_pos + 1:]
                            break
        finally:
            f.close()

        return output 

    def __init__(self, logger, line_pattern, datafile):
        if isinstance(line_pattern, (str, unicode)):
            self.line_pattern = re.compile(line_pattern)
        else:
            self.line_pattern = line_pattern
                
        self._dogstream = Dogstream(logger, datafile, self._parse_line)
    
    def _get_metric_prefix(self, data):
        # Should be overridded by subclasses
        return [self.metric_prefix]

    def _parse_line(self, logger, line):
        matched = self.line_pattern.match(line)
        output = []
        if matched:
            data = matched.groupdict()
            metric_prefix = self._get_metric_prefix(data)
            
            # Parse the prefdata values, which are a space-delimited list of:
            #   'label'=value[UOM];[warn];[crit];[min];[max]
            perf_data = data.get(self.perfdata_field, '').split(' ')
            for pair in perf_data:
                pair_match = self.pair_pattern.match(pair)
                if not pair_match:
                    continue
                else:
                    pair_data = pair_match.groupdict()
                
                label = pair_data['label']
                timestamp = data.get('TIMET', '')
                value = pair_data['value']
                attributes = {'metric_type': 'gauge'}

                if '/' in label:
                    # Special case: if the label begins
                    # with a /, treat the label as the device
                    # and use the metric prefix as the metric name
                    metric = '.'.join(metric_prefix)
                    attributes['device_name'] = label

                else:
                    # Otherwise, append the label to the metric prefix
                    # and use that as the metric name
                    metric = '.'.join(metric_prefix + [label])

                host_name = data.get('HOSTNAME', None)
                if host_name:
                    attributes['host_name'] = host_name

                optional_keys = ['unit', 'warn', 'crit', 'min', 'max']
                for key in optional_keys:
                    attr_val = pair_data.get(key, None)
                    if attr_val is not None and attr_val != '':
                        attributes[key] = attr_val

                output.append((
                    metric,
                    timestamp,
                    value,
                    attributes
                ))
        return output

    def check(self, agentConfig, move_end=True):
        return self._dogstream.check(agentConfig, move_end)


class NagiosHostPerfData(NagiosPerfData):
    perfdata_field = 'HOSTPERFDATA'

    @classmethod
    def init(cls, logger, nagios_config):
        host_perfdata_file_template = nagios_config.get('host_perfdata_file_template', None)
        host_perfdata_file = nagios_config.get('host_perfdata_file', None)

        if host_perfdata_file_template and host_perfdata_file:
            host_pattern = cls.template_regex(host_perfdata_file_template)
            return cls(logger, host_pattern, host_perfdata_file)
        else:
            return None

    def _get_metric_prefix(self, line_data):
        return [self.metric_prefix, 'host']


class NagiosServicePerfData(NagiosPerfData):
    perfdata_field = 'SERVICEPERFDATA'

    @classmethod
    def init(cls, logger, nagios_config):
        service_perfdata_file_template = nagios_config.get('service_perfdata_file_template', None)
        service_perfdata_file = nagios_config.get('service_perfdata_file', None)

        if service_perfdata_file_template and service_perfdata_file:
            service_pattern = cls.template_regex(service_perfdata_file_template)
            return cls(logger, service_pattern, service_perfdata_file)
        else:
            return None

    def _get_metric_prefix(self, line_data):
        metric = [self.metric_prefix] 
        middle_name = line_data.get('SERVICEDESC', None)
        if middle_name:
            metric.append(middle_name.replace(' ', '_').lower())
        return metric


# Allow a smooth uninstall of previous version
class RollupLP: pass


class DdForwarder(object):

    QUEUE_SIZE  = "queue_size"
    QUEUE_COUNT = "queue_count"

    RE_QUEUE_STAT = re.compile(r"\[.*\] Queue size: at (.*), (\d+) transaction\(s\), (\d+) KB")

    def __init__(self, logger, config):
        self.log_path = config.get('ddforwarder_log', '/var/log/ddforwarder.log')
        self.logger = logger
        self._gen = None

    def _init_metrics(self):
        self.metrics = {}
   
    def _add_metric(self, name, value, ts):

        if self.metrics.has_key(name):
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

            return { 'ddforwarder': self.metrics }
        else:
            self.logger.debug("Can't tail datadog forwarder log file: %s" % self.log_path)
            return {}


def testDogStream():
    import logging
    
    logger = logging.getLogger("datadog")
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.StreamHandler())
    dogstream = Dogstream(logger)

    while True:
        events = dogstream.check({'apiKey':'my_apikey', 'dogstream_log': sys.argv[1]}, move_end=True)
        for e in events:
            print "Event:", e
        time.sleep(5)

def testddForwarder():
    import logging
    
    logger = logging.getLogger("datadog")
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.StreamHandler())

    config = {'apiKey':'my_apikey', 'ddforwarder_log': sys.argv[1]}
    dd = DdForwarder(logger, config)
    m = dd.check(config, move_end=False)
    while True:
        print m
        time.sleep(5)
        m = dd.check(config)


if __name__ == '__main__':
    testddForwarder()
