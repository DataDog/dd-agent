"""
Custom parser for nginx log suitable for use by Datadog 'dogstreams'.
To use, add to datadog.conf as follows:
    dogstreams: [path to ngnix log (e.g: "/var/log/nginx/access.log"]:[path to this python script (e.g "/usr/share/datadog/agent/dogstream/nginx.py")]:[name of parsing method of this file ("parse")]
so, an example line would be:
    dogstreams: /var/log/nginx/access.log:/usr/share/datadog/agent/dogstream/nginx.py:parse
Log of nginx should be defined like that:
    log_format time_log '$time_local "$request" S=$status $bytes_sent T=$request_time R=$http_x_forwarded_for';
when starting dd-agent, you can find the collector.log and check if the dogstream initialized successfully
    """
from datetime import datetime
import time
import re

# mapping between datadog and supervisord log levels
METRIC_TYPES = {
    'AVERAGE_RESPONSE': 'nginx.net.avg_response',
    'FIVE_HUNDRED_STATUS': 'nginx.net.5xx_status'
}

TIME_REGEX = "\sT=[-+]?[0-9]*\.?[0-9]+\s*"
TIME_REGEX_SPLIT = re.compile("T=")
STATUS_REGEX = "\sS=+5[0-9]{2}\s"

def parse(log, line):
    if len(line) == 0:
        log.info("Skipping empty line")
        return None
    timestamp = getTimestamp(line)
    avgTime = parseAvgTime(line)
    objToReturn = []
    if isHttpResponse5XX(line):
        objToReturn.append((METRIC_TYPES['FIVE_HUNDRED_STATUS'], timestamp, 1, {'metric_type': 'counter'}))
    if avgTime is not None:
        objToReturn.append((METRIC_TYPES['AVERAGE_RESPONSE'], timestamp, avgTime, {'metric_type': 'gauge'}))
    return objToReturn

def getTimestamp(line):
    line_parts = line.split()
    dt = line_parts[0]
    date = datetime.strptime(dt, "%d/%b/%Y:%H:%M:%S")
    date = time.mktime(date.timetuple())
    return date

def parseAvgTime(line):
    time = re.search(TIME_REGEX, line)
    if time is not None:
        time = time.group(0)
        time = TIME_REGEX_SPLIT.split(time)
        if len(time) == 2:
            return float(time[1])
        return None

def isHttpResponse5XX(line):
    response = re.search(STATUS_REGEX, line)
    return (response is not None)

if __name__ == "__main__":
    import sys
    import pprint
    import logging
    logging.basicConfig()
    log = logging.getLogger()
    lines = open(sys.argv[1]).readlines()
    pprint.pprint([parse(log, line) for line in lines])