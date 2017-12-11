"""
DogStream parser capible of reading Apache Common and Combined logging formats.

Parser will generate two metrics
1.) apache.net.requests
2.) apache.net.request_size

Both metrics will be tagged with 'status' code family (2xx, 3xx, 4xx, 5xx, etc)
and HTTP 'verb' (GET, PUT, POST, etc)

To parse common logs add the following to your agent configuration
dogstreams: /var/log/httpd/access.log:/etc/dd-agent/dogstream/apache.py:parse_common

To parse combined logs add the following to your agent configuration
dogstreams: /var/log/httpd/access.log:/etc/dd-agent/dogstream/apache.py:parse_combined

both config lines assume your logs are in /var/log/httpd/access.log and this file is
at /etc/dd-agent/dogstream/apache.py

"""
import time
from datetime import datetime
import re

# Adapted from http://www.leancrew.com/all-this/2013/07/parsing-my-apache-logs/
# Regex for the Apache common log format.
COMBINED_PATTERN_PARTS = [
    r'(?P<host>\S+)',                   # host %h
    r'\S+',                             # indent %l (unused)
    r'(?P<user>\S+)',                   # user %u
    r'\[(?P<time>.+)\]',                # time %t
    r'"(?P<verb>[A-Z]+)',               # HTTP Verb (GET, POST, etc)
    r'(?P<request>.*)"',                # request "%r" (minus verb)
    r'(?P<status>[0-9]+)',              # status %>s
    r'(?P<size>\S+)',                   # size %b (careful, can be '-')
    r'"(?P<referrer>.*)"',              # referrer "%{Referer}i"
    r'"(?P<agent>.*)"'                  # user agent "%{User-agent}i"
]

COMMON_PATTERN_PARTS = [
    r'(?P<host>\S+)',                   # host %h
    r'\S+',                             # indent %l (unused)
    r'(?P<user>\S+)',                   # user %u
    r'\[(?P<time>.+)\]',                # time %t
    r'"(?P<verb>[A-Z]+)',               # HTTP Verb (GET, POST, etc)
    r'(?P<request>.*)"',                # request "%r" (minus verb)
    r'(?P<status>[0-9]+)',              # status %>s
    r'(?P<size>\S+)'                    # size %b (careful, can be '-')
]

COMBINED_PATTERN = re.compile(r'\s+'.join(COMBINED_PATTERN_PARTS)+r'\s*\Z')
COMMON_PATTERN = re.compile(r'\s+'.join(COMMON_PATTERN_PARTS)+r'\s*\Z')

def parse_common(logger, line):
    return build_message(parse_line(line, COMMON_PATTERN))
    #foo

def parse_combined(logger, line):
    return build_message(parse_line(line, COMBINED_PATTERN))

def parse_line(line, regex):

    match = regex.match(line)

    if match:
        return match.groupdict()
    else:
        return {}

def build_message(raw_data):
    return_value = []

    # Convert apache time to epoch or use system time
    # TODO: may be better to have this as a try block
    if 'time' in raw_data:
        timestamp = getTimestamp(raw_data["time"])
    else:
        raw_data['time'] = time.time()

    # In 300 and 400 responses size may be -
    if raw_data['size'].isdigit():
        raw_data['size'] = int(raw_data['size'])
    else:
        raw_data['size'] = 0

    status_code_family = raw_data['status'][0] + 'xx'
    return_value.append(('apache.net.requests', timestamp, 1, {'metric_type': 'counter',
                                                               'unit': 'request',
                                                               'status': status_code_family,
                                                               'verb': raw_data['verb']}))

    return_value.append(('apache.net.request_size', timestamp,
                        raw_data["size"], {'metric_type': 'histogram',
                                           'unit': 'bytes',
                                           'status': status_code_family,
                                           'verb': raw_data['verb']}))

    return return_value

#borrowed from the nginx dogstream example
# parse apache time 27/Oct/2000:09:27:09 -0400
def getTimestamp(line):
    line_parts = line.split()
    dt = line_parts[0]
    date = datetime.strptime(dt, "%d/%b/%Y:%H:%M:%S")
    date = time.mktime(date.timetuple())
    return date

def parse_web(logger, line):
    # Split the line into fields
    date, metric_name, metric_value, attrs = line.split('|')

    # Convert the iso8601 date into a unix timestamp, assuming the timestamp
    # string is in the same timezone as the machine that's parsing it.
    date = datetime.strptime(date, "%Y-%m-%dT%H:%M:%S")
    date = time.mktime(date.timetuple())

    # Remove surrounding whitespace from the metric name
    metric_name = metric_name.strip()

    # Convert the metric value into a float
    metric_value = float(metric_value.strip())

    # Convert the attribute string field into a dictionary
    attr_dict = {}
    for attr_pair in attrs.split(','):
        attr_name, attr_val = attr_pair.split('=')
        attr_name = attr_name.strip()
        attr_val = attr_val.strip()
        attr_dict[attr_name] = attr_val

    # Return the output as a tuple
    return (metric_name, date, metric_value, attr_dict)

def test():
    import pprint
    import logging
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger()


    # Set up the test input and expected output
    test_common = '123.123.123 - - [12/Aug/2015:10:06:39 -0400] "PUT /my/path?foo=bar&baz=boom HTTP/1.1" 200 52'
    test_combined = '123.45.67.89 - - [27/Oct/2000:09:27:09 -0400] "GET /java/javaResources.html HTTP/1.0" 200 10450 "-" "Mozilla/4.6 [en] (X11; U; OpenBSD 2.8 i386; Nav)"'

    common = parse_common(logger, test_common)
    combined = parse_combined(logger, test_combined)

    pprint.pprint(common)
    pprint.pprint(combined)

if __name__ == '__main__':
    # For local testing, callable as "python /path/to/parsers.py"
    test()
