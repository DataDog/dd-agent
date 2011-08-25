from utils import TailFile, median
import os
import sys
import traceback
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
                self.logger.error('Could not load Dogstream line parser "%s"' % (
                    config['dogstream_line_parser'], 
                    os.pathsep.join(sys.path))
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
            metric, ts, value, attrs = self.parse_func(self.logger, line)
            
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
                self.logger.warn('Invalid line (%s): "%s"', 
                    ', '.join(invalid_reasons), line)
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



if __name__ == '__main__':
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



