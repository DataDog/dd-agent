from utils import TailFile, median
import os
import sys
import traceback
import re
import time
from datetime import datetime

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

class Dogstream(object):
    def __init__(self, logger, config):
        self.log_path = config.get('dogstream_log', None)
        self.gen = None
        self.values = None
        self.logger = logger
        self.parse_func = None
        
        # Allow for user-supplied line parsers
        if 'dogstream_line_parser' in config:
            try:
                module_name, func_name = config['dogstream_line_parser'].split(':')
                self.parse_func = getattr(__import__(module_name), func_name, 
                    None)
            except:
                self.logger.exception(traceback.format_exc())
                self.logger.error('Could not load Dogstream line parser "%s" PYTHONPATH=%s' % (
                    config['dogstream_line_parser'], 
                    os.environ.get('PYTHONPATH', ''))
                )
                
        if self.parse_func is None:
            self.parse_func = self._default_line_parser
    
    def check(self, agentConfig, move_end=True):
        if self.log_path:
            
            self.values = []
        
            # Build our tail -f
            if self.gen is None:
                self.gen = TailFile(self.logger, self.log_path, self._line_parser).tail(line_by_line=False, move_end=move_end)

            # read until the end of file
            try:
                self.gen.next()
                self.logger.debug("Done dogstream check for file %s, found %s metric points" % (self.log_path, len(self.values)))
            except StopIteration, e:
                self.logger.exception(e)
                self.logger.warn("Can't tail {0} file".format(self.log_path))
            
            return self._aggregate(self.values)
        else:
            return {}

    
    def _line_parser(self, line):
        try:
            parsed = self.parse_func(self.logger, line)
            if parsed is None:
                return
            
            if isinstance(parsed, tuple):
                parsed = [parsed]
            
            for metric_tuple in parsed:
                try:
                    metric, ts, value, attrs = metric_tuple
                except:
                    continue
                
                # Validation
                invalid_reasons = []
                try:
                    ts = float(ts)
                    date = datetime.fromtimestamp(ts)
                    assert date.year > 1990
                except Exception:
                    invalid_reasons.append('invalid timestamp')

                try:
                    value = float(value)
                except Exception:
                    invalid_reasons.append('invalid metric value')

                if invalid_reasons:
                    self.logger.warn('Invalid parsed values %s (%s): "%s"', 
                        repr(metric_tuple), ', '.join(invalid_reasons), line)
                else:
                    self.values.append((metric, ts, value, attrs))
        except Exception:
            self.logger.exception(traceback.format_exc())
    
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
                key, val = keyval.split('=')
                attributes[key] = val
        except Exception, e:
            logger.warn(traceback.format_exc())
        
        return metric, timestamp, value, attributes
        

    
    def _aggregate(self, values):
        gauges = {}
        counters = {}
        timestamps = {}
        
        # Aggregate the metrics by their metric_type (defined in attributes)
        for metric, timestamp, value, attributes in values:
            # FIXME: Ignoring timestamp at this point because
            # the metric etl ignores it, but we should take the 
            # average of the timestamps to be the timestamp of the metric
            # point.
            
            # Store metric value based on what type it is
            if metric in counters:
                counters[metric] += value
            elif metric in gauges:
                gauges[metric].append(value)
            else:
                metric_type = attributes.get('metric_type', 'gauge')
                if metric_type == 'counter':
                    counters[metric] = value
                else:
                    gauges[metric] = [value]
        
        check_output = {}
        
        # Combine the counter and gauge values into a single dict
        check_output.update(counters)
        for metric, metric_vals in gauges.items():
            check_output[metric] = median(metric_vals)
        
        return check_output



# Allow a smooth uninstall of previous version
class RollupLP: pass


class DdForwarder(object):

    QUEUE_SIZE  = "queue_size"
    QUEUE_COUNT = "queue_count"

    RE_QUEUE_STAT = re.compile(r"\[.*\] Queue size: at (.*), (\d+) transaction\(s\), (\d+) KB")

    def __init__(self, logger, config):
        self.log_path = config.get('ddforwarder_log', '/var/log/ddforwarder.log')
        self.logger = logger
        self.gen = None

    def _init_metrics(self):
        self.metrics = {}
   
    def _add_metric(self,name,value,ts):

        if self.metrics.has_key(name):
            self.metrics[name].append((ts,value))
        else:
            self.metrics[name] = [(ts,value)]
 
    def _parse_line(self,line):

        try:
            m = self.RE_QUEUE_STAT.match(line)
            if m is not None:
                ts, count, size = m.groups()
                self._add_metric(self.QUEUE_SIZE,size,round(float(ts)))
                self._add_metric(self.QUEUE_COUNT,count,round(float(ts)))
        except Exception, e:
            self.logger.exception(e)

    def check(self, agentConfig, move_end=True):

        if self.log_path and os.path.isfile(self.log_path):
            
            #reset metric points
            self._init_metrics()

            # Build our tail -f
            if self.gen is None:
                self.gen = TailFile(self.logger, self.log_path, self._parse_line).tail(line_by_line=False, 
                    move_end=move_end)

            # read until the end of file
            try:
                self.gen.next()
                self.logger.debug("Done ddforwarder check for file %s" % (self.log_path))
            except StopIteration, e:
                self.logger.exception(e)
                self.logger.warn("Can't tail {0} file".format(self.log_path))            

            return { 'ddforwarder': self.metrics }
        else:
            self.logger.debug("Can't tail datadog forwarder log file: %s" % self.log_path)
            return {}
            

def testDogStream():
    import logging
    import sys
    import time
    
    logger = logging.getLogger("datadog")
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.StreamHandler())
    dogstream = Dogstream(logger)

    while True:
        events = dogstream.check({'apiKey':'my_apikey','dogstream_log': sys.argv[1]}, move_end=True)
        for e in events:
            print "Event:", e
        time.sleep(5)

def testddForwarder():
    import logging
    import sys
    import time
    
    logger = logging.getLogger("datadog")
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.StreamHandler())

    config = {'apiKey':'my_apikey','ddforwarder_log': sys.argv[1]}
    dd = DdForwarder(logger,config)
    m = dd.check(config, move_end=False)
    while True:
        print m
        time.sleep(5)
        m = dd.check(config)


if __name__ == '__main__':
    testddForwarder()
