import os
import re
import time
import datetime
from stat import *
from utils import TailFile

def build_re(log_level, regexp):
    return re.compile('^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d*)' + ' ' + log_level + ' (.*:\d*) ' + regexp)

class RollupLP(object):
    """Rollup log parser"""

    key = "rollup"

    # Parsing states
    INIT     = 0
    LOOK_END = 1

    # Regexp
    date_format = "%Y-%m-%d %H:%M:%S,%f"
    start_re = build_re('INFO','About to rollup (\d*) series at (\D{1}) resolution')
    end_re = build_re('INFO','Rolledup (\d*) series at (\D{1}) resolution')

    def __init__(self):
        self.state = RollupLP.INIT
        self.context = None
        self.logger = None
        self.gen = None
        self.metrics = None

    @staticmethod
    def _string_to_date(string):
        return datetime.datetime.strptime(string,RollupLP.date_format)

    @staticmethod
    def _td_to_ms(td):
        """Convert a time delta to milliseconds"""    
        return int((td.microseconds / 1000) + (td.seconds + td.days * 24 * 3600) * 1000)

    @staticmethod
    def _dt_to_ts(dt):
        """Convert a datetime to a timestamp"""
        return int(time.mktime(dt.timetuple()))

    def _add_to_metric(self,key,ts,value):
        tp = (ts,value)
        if self.metrics.has_key(key):
            self.metrics[key].append(tp)
        else:
            self.metrics[key] = [tp]

    def _process_init(self,line):
        m = self.start_re.match(line)
        if m is not None:
            (date, line, number, resolution) = m.groups()
            self.context = { 'res': resolution,
                             'start': self._string_to_date(date),
                             'number': number
                            }
            self.state = RollupLP.LOOK_END

    def _process_end(self,line):
        m = self.end_re.match(line)
        if m is not None:
            (date, line, number, resolution) =  m.groups()
            end = self._string_to_date(date)
            c_res = self.context['res']
            c_start = self.context['start']

            if c_res == resolution:
                ts = RollupLP._dt_to_ts(end)
                self._add_to_metric('%s.total' % c_res, \
                                    ts, \
                                    RollupLP._td_to_ms(end - c_start))

                self._add_to_metric('%s.count' % c_res, ts, number)

                self.logger.debug("Processed %s series at res %s" % (number, c_res))

            self.context = None
            self.state = RollupLP.INIT

    def _parse_line(self, line):

        if self.state == RollupLP.INIT:
            return self._process_init(line)
        elif self.state == RollupLP.LOOK_END:
            return self._process_end(line)
 
    def check(self, logger, agentConfig):
        self.logger = logger

        log_path = agentConfig.get('datadog_etl_rollup_logs', None)
        if log_path is None:
            return False

        if self.gen is None:
            self.gen = TailFile(logger, log_path, self._parse_line).tail(move_end = True) #FIXME
        
        self.metrics = {}

        # Read until the EOF
        try:
            self.gen.next()
            self.logger.debug("Done checking ETL Rollup log {0}".format(log_path))
        except StopIteration, e:
            self.logger.exception(e)
            self.logger.warn("Can't tail file {0}".format(log_path))

        self.logger.debug("datadog ETL returns: %s" % str(self.metrics))
        return self.metrics

if __name__ == "__main__":

    import logging
    import time
    logger = logging.getLogger("nagios")
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.StreamHandler())

    rlp = RollupLP()

    while True:
        rlp.check(logger, {
            'datadog_etl_rollup_logs':'/home/fabrice/dev/datadog/git/dogweb/build/rollup_etl.log'
            })
        time.sleep(1)
