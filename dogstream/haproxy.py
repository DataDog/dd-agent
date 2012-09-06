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


Outputted metrics:
    haproxy.http.tq
    haproxy.http.tw
    haproxy.http.tc
    haproxy.http.tr
    haproxy.http.tt
    haproxy.http.status_code.<status_code>
    haproxy.http.frontend_name
    haproxy.http.backend_name
    haproxy.http.server_name
    haproxy.http.bytes_read
    haproxy.http.actconn
    haproxy.http.feconn
    haproxy.http.beconn
    haproxy.http.srv_conn
    haproxy.http.retries
    haproxy.http.srv_queue
    haproxy.http.backend_queue
"""

from datetime import datetime
import time
import logging

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

def parse_haproxy(logger, line):
    tokens = [
        ('syslog_timestamp',    ' '),
        ('syslog_host',         ' '),
        ('process_name',        '['),
        ('pid',                 ']: '),
        ('client_ip',           ':'),
        ('client_port',         ' ['),
        ('accept_date',         '] '),
        ('frontend_name',       ' '),
        ('backend_name',        '/'),
        ('server_name',         ' '),
        ('haproxy.http.tq',                  '/'),
        ('haproxy.http.tw',                  '/'),
        ('haproxy.http.tc',                  '/'),
        ('haproxy.http.tr',                  '/'),
        ('haproxy.http.tt',                  ' '),
        ('status_code',         ' '),
        ('haproxy.http.bytes_read',          ' '),
        ('captured_request_cookie', ' '),
        ('captured_response_cookie', ' '),
        ('termination_state',   ' '),
        ('haproxy.http.actconn',             '/'),
        ('haproxy.http.feconn',              '/'),
        ('haproxy.http.beconn',              '/'),
        ('haproxy.http.srv_conn',            '/'),
        ('haproxy.http.retries',             ' '),
        ('haproxy.http.srv_queue',           '/'),
        ('haproxy.http.backend_queue',       ' "'),
        ('http_request',        '"'),
    ]
    data = {}
    points = []
    rest = line
    for key, stop_token in tokens:
        val, _, rest = rest.partition(stop_token)
        data[key] = val

    if not data.get('accept_date', ''):
        return None
    try:
        timestamp = parse_timestamp(data['accept_date'])
    except:
        return None
    if data.get('server_name') in (None, '<STATS>'):
        return None
    device_name = '%s:%s' % (data['backend_name'], data['server_name'])
    attributes = {'metric_type': 'counter',
                  'tags': ['backend:%s' % data['backend_name']]}
    url_tag = stem_url(data.get('http_request').split()[1])
    if url_tag:
        attributes['tags'].append('url:%s' % url_tag)

    metrics = [
        'haproxy.http.tq',
        'haproxy.http.tw',
        'haproxy.http.tc',
        'haproxy.http.tr',
        'haproxy.http.tt',
        'haproxy.http.bytes_read',
        'haproxy.http.actconn',
        'haproxy.http.feconn',
        'haproxy.http.beconn',
        'haproxy.http.srv_conn',
        'haproxy.http.retries',
        'haproxy.http.srv_queue',
        'haproxy.http.backend_queue',
    ]

    for metric in metrics:
        value = data.get(metric, None)
        if value is not None:
            try:
                value = int(float(value))
            except Exception:
                pass
            else:
                points.append((metric, timestamp, value, attributes))

    status_code = data.get('status_code', None)
    if status_code:
        points.append(('haproxy.http.status.%s' % status_code, timestamp, 1, attributes))

    return points

if __name__ == '__main__':
    # Parse stdin and extract metrics
    import sys
    logging.basicConfig(format="%(asctime)s %(levelname)s %(filename)s:%(lineno)d %(message)s")
    while True:
        line = sys.stdin.readline()
        if line is None or len(line) == 0:
            break
        else:
            print(parse_haproxy(logging.getLogger(), line))
