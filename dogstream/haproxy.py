"""Haproxy log parser.

Log format (from section 8.2.3 of http://haproxy.1wt.eu/download/1.3/doc/configuration.txt):

  Field   Format                                Extract from the example above
      1   process_name '[' pid ']:'                            haproxy[14389]:
      2   client_ip ':' client_port                             10.0.1.2:33317
      3   '[' accept_date ']'                       [06/Feb/2009:12:14:14.655]
      4   frontend_name                                                http-in
      5   backend_name '/' server_name                             static/srv1
      6   Tq '/' Tw '/' Tc '/' Tr '/' Tt*                       10/0/30/69/109
      7   status_code                                                      200
      8   bytes_read*                                                     2750
      9   captured_request_cookie                                            -
     10   captured_response_cookie                                           -
     11   termination_state                                               ----
     12   actconn '/' feconn '/' beconn '/' srv_conn '/' retries*    1/1/1/1/0
     13   srv_queue '/' backend_queue                                      0/0
     14   '{' captured_request_headers* '}'                   {haproxy.1wt.eu}
     15   '{' captured_response_headers* '}'                                {}
     16   '"' http_request '"'                      "GET /index.html HTTP/1.1"

Output metrics:
"""

from datetime import datetime
import time
import logging
import re

HAPROXY_RE = re.compile("^.*haproxy\[(?P<pid>\d+)\]: (?P<client_ip>[\d.]+):(?P<client_port>\d+) \[(?P<accept_date>[^]]+)\] (?P<frontend_name>\w+) (?P<backend_name>\w+)/(?P<server_name>\S+) (?P<tq>-?\d+)/(?P<tw>-?\d+)/(?P<tc>-?\d+)/(?P<tr>-?\d+)/(?P<tt>-?\d+) (?P<status_code>\d{3}) (?P<bytes_read>\d+) . . .... (?P<actconn>\d+)/(?P<feconn>\d+)/(?P<beconn>\d+)/(?P<srvconn>\d+)/(?P<retries>\d+) (?P<srv_queue>\d+)/(?P<backend_queue>\d+).*\"(?P<cmd>\w+) (?P<url>\S+) HTTP/.\..\"$")

def parse_timestamp(timestamp):
    return time.mktime(datetime.strptime(timestamp, '%d/%b/%Y:%H:%M:%S.%f').timetuple())

def stem_url(url):
    """Remove unneeded variability in URLs"""
    try:
        # First ditch parameters after ?
        # Then remove all digits
        return url.split("?")[0].translate(None, "0123456789")
    except:
        return None

def parse_status_code(counters, code, lbound, ubound, metric):
    assert lbound < ubound
    if int(code) >= lbound and int(code) <= ubound:
        counters[metric] += 1
    return counters

def parse_haproxy(logger, line, state):
    points = []
    # Simple init of status codes counters
    if len(state) == 0:
        state['codes'] = {'2xx': 0, '3xx': 0, '4xx': 0, '5xx': 0}
        state['aborts'] = 0

    m = HAPROXY_RE.match(line)
    # No match? skip
    if m is None:
        return None

    timestamp = parse_timestamp(m.group('accept_date'))
    # Skip STATS call
    if m.group('server_name') == '<STATS>':
        return None

    attributes = {'tags': ['service:%s' % m.group('backend_name')]}
    cmd = m.group('cmd')
    # url_tag = stem_url(m.group('url'))
    # if url_tag:
    #     attributes['tags'].append('url:%s' % url_tag)

    # status codes
    parse_status_code(state['codes'], m.group('status_code'), 200, 299, '2xx')
    parse_status_code(state['codes'], m.group('status_code'), 300, 399, '3xx')
    parse_status_code(state['codes'], m.group('status_code'), 400, 499, '4xx')
    parse_status_code(state['codes'], m.group('status_code'), 500, 599, '5xx')

    metrics = [
        ('haproxy.http.tq', 'gauge', lambda d: int(d.group('tq'))),
        ('haproxy.http.tw', 'gauge', lambda d: int(d.group('tw'))),
        ('haproxy.http.tc', 'gauge', lambda d: int(d.group('tc'))),
        ('haproxy.http.tr', 'gauge', lambda d: int(d.group('tr'))),
        ('haproxy.http.tt', 'gauge', lambda d: int(d.group('tt'))),
        ('haproxy.http.bytes_read', 'gauge', lambda d: d.group('bytes_read')),
        ('haproxy.http.2xx', 'counter', lambda m, s=state: s['codes']['2xx']),
        ('haproxy.http.3xx', 'counter', lambda m, s=state: s['codes']['3xx']),
        ('haproxy.http.4xx', 'counter', lambda m, s=state: s['codes']['4xx']),
        ('haproxy.http.5xx', 'counter', lambda m, s=state: s['codes']['5xx']),
    ]

    is_abort = False
    for name, typ, accessor in metrics:
        value = accessor(m)
        try:
            value = int(value)
        except:
            pass
        else:
            # Treat -1 in timing as an abort and skip the metric
            if value == -1 and name[-2:] in ('tq', 'tw', 'tc', 'tr', 'tt'):
                if not is_abort:
                    state['aborts'] += 1
                    points.append(('haproxy.http.abort', timestamp, state['aborts'], {'metric_type': 'counter'}))
                    is_abort = True
            else:
                points.append((name, timestamp, value, attributes))
    return points

if __name__ == '__main__':
    # Parse stdin and extract metrics
    import sys
    import pprint
    state = {}
    logging.basicConfig(format="%(asctime)s %(levelname)s %(filename)s:%(lineno)d %(message)s")
    while True:
        line = sys.stdin.readline()
        if line is None or len(line) == 0:
            break
        else:
            r = parse_haproxy(logging.getLogger(), line, state)
            if r is not None:
                pprint.pprint(r)
