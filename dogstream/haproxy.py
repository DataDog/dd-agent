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
import calendar

def parse_timestamp(timestamp):
    return calendar.timegm(datetime.strptime(timestamp, '%d/%b/%Y:%H:%M:%S.%f').timetuple())

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
    except Exception:
        return None
    device_name = '%s:%s' % (data['backend_name'], data['server_name'])
    attributes = {'metric_type': 'counter', 'device_name': device_name}
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

def test_haproxy():
    haproxy_sample = """2011-11-11T20:33:50+00:00 localhost haproxy[14992]: 127.0.0.1:58067 [11/Nov/2011:20:33:50.639] dogarchive-frontend dogarchive-backend/dogarchive-3 0/0/0/45/46 200 132 - - ---- 17/0/0/0/0 0/0 "POST /intake HTTP/1.1"
2011-11-11T20:33:52+00:00 localhost haproxy[14992]: 10.212.98.197:1367 [11/Nov/2011:20:33:51.005] public dogdispatcher/ip-10-114-117-234 970/0/1/47/1018 202 113 - - ---- 16/16/0/0/0 0/0 "POST /intake/ HTTP/1.1"
2011-11-11T20:33:53+00:00 localhost haproxy[14992]: 127.0.0.1:58090 [11/Nov/2011:20:33:53.701] dogarchive-frontend dogarchive-backend/dogarchive-2 0/0/0/33/34 200 132 - - ---- 17/0/0/0/0 0/0 "POST /intake HTTP/1.1"
2011-11-11T20:33:59+00:00 localhost haproxy[14992]: 10.212.98.197:1391 [11/Nov/2011:20:33:58.295] public dogweb/<STATS> 882/-1/-1/-1/883 200 23485 - - PR-- 16/16/0/0/0 0/0 "GET /admin?stats HTTP/1.1"
2011-11-11T20:34:02+00:00 localhost haproxy[14992]: 10.84.199.126:37639 [11/Nov/2011:20:34:02.113] public public/<NOSRV> 0/-1/-1/-1/0 302 126 - - PR-- 17/17/0/0/0 0/0 "GET /status/pingdom?window=15 HTTP/1.1"
2011-11-11T20:34:02+00:00 localhost haproxy[14992]: 10.212.98.197:1406 [11/Nov/2 """

    expected = [
        [
            ('haproxy.http.tq', 1321043630, 0, {'metric_type':'counter', 'device_name': 'dogarchive-backend:dogarchive-3'}),
            ('haproxy.http.tw', 1321043630, 0, {'metric_type':'counter', 'device_name': 'dogarchive-backend:dogarchive-3'}),
            ('haproxy.http.tc', 1321043630, 0, {'metric_type':'counter', 'device_name': 'dogarchive-backend:dogarchive-3'}),
            ('haproxy.http.tr', 1321043630, 45, {'metric_type':'counter', 'device_name': 'dogarchive-backend:dogarchive-3'}),
            ('haproxy.http.tt', 1321043630, 46, {'metric_type':'counter', 'device_name': 'dogarchive-backend:dogarchive-3'}),
            ('haproxy.http.bytes_read', 1321043630, 132, {'metric_type':'counter', 'device_name': 'dogarchive-backend:dogarchive-3'}),
            ('haproxy.http.actconn', 1321043630, 17, {'metric_type':'counter', 'device_name': 'dogarchive-backend:dogarchive-3'}),
            ('haproxy.http.feconn', 1321043630, 0, {'metric_type':'counter', 'device_name': 'dogarchive-backend:dogarchive-3'}),
            ('haproxy.http.beconn', 1321043630, 0, {'metric_type':'counter', 'device_name': 'dogarchive-backend:dogarchive-3'}),
            ('haproxy.http.srv_conn', 1321043630, 0, {'metric_type':'counter', 'device_name': 'dogarchive-backend:dogarchive-3'}),
            ('haproxy.http.retries', 1321043630, 0, {'metric_type':'counter', 'device_name': 'dogarchive-backend:dogarchive-3'}),
            ('haproxy.http.srv_queue', 1321043630, 0, {'metric_type':'counter', 'device_name': 'dogarchive-backend:dogarchive-3'}),
            ('haproxy.http.backend_queue', 1321043630, 0, {'metric_type':'counter', 'device_name': 'dogarchive-backend:dogarchive-3'}),
            ('haproxy.http.status.200', 1321043630, 1, {'metric_type':'counter', 'device_name': 'dogarchive-backend:dogarchive-3'}),
        ],
        [
            ('haproxy.http.tq', 1321043631, 970, {'metric_type':'counter', 'device_name': 'dogdispatcher:ip-10-114-117-234'}),
            ('haproxy.http.tw', 1321043631, 0, {'metric_type':'counter', 'device_name': 'dogdispatcher:ip-10-114-117-234'}),
            ('haproxy.http.tc', 1321043631, 1, {'metric_type':'counter', 'device_name': 'dogdispatcher:ip-10-114-117-234'}),
            ('haproxy.http.tr', 1321043631, 47, {'metric_type':'counter', 'device_name': 'dogdispatcher:ip-10-114-117-234'}),
            ('haproxy.http.tt', 1321043631, 1018, {'metric_type':'counter', 'device_name': 'dogdispatcher:ip-10-114-117-234'}),
            ('haproxy.http.bytes_read', 1321043631, 113, {'metric_type':'counter', 'device_name': 'dogdispatcher:ip-10-114-117-234'}),
            ('haproxy.http.actconn', 1321043631, 16, {'metric_type':'counter', 'device_name': 'dogdispatcher:ip-10-114-117-234'}),
            ('haproxy.http.feconn', 1321043631, 16, {'metric_type':'counter', 'device_name': 'dogdispatcher:ip-10-114-117-234'}),
            ('haproxy.http.beconn', 1321043631, 0, {'metric_type':'counter', 'device_name': 'dogdispatcher:ip-10-114-117-234'}),
            ('haproxy.http.srv_conn', 1321043631, 0, {'metric_type':'counter', 'device_name': 'dogdispatcher:ip-10-114-117-234'}),
            ('haproxy.http.retries', 1321043631, 0, {'metric_type':'counter', 'device_name': 'dogdispatcher:ip-10-114-117-234'}),
            ('haproxy.http.srv_queue', 1321043631, 0, {'metric_type':'counter', 'device_name': 'dogdispatcher:ip-10-114-117-234'}),
            ('haproxy.http.backend_queue', 1321043631, 0, {'metric_type':'counter', 'device_name': 'dogdispatcher:ip-10-114-117-234'}),
            ('haproxy.http.status.202', 1321043631, 1, {'metric_type':'counter', 'device_name': 'dogdispatcher:ip-10-114-117-234'}),
        ],
        [
            ('haproxy.http.tq', 1321043633, 0, {'metric_type':'counter', 'device_name': 'dogarchive-backend:dogarchive-2'}),
            ('haproxy.http.tw', 1321043633, 0, {'metric_type':'counter', 'device_name': 'dogarchive-backend:dogarchive-2'}),
            ('haproxy.http.tc', 1321043633, 0, {'metric_type':'counter', 'device_name': 'dogarchive-backend:dogarchive-2'}),
            ('haproxy.http.tr', 1321043633, 33, {'metric_type':'counter', 'device_name': 'dogarchive-backend:dogarchive-2'}),
            ('haproxy.http.tt', 1321043633, 34, {'metric_type':'counter', 'device_name': 'dogarchive-backend:dogarchive-2'}),
            ('haproxy.http.bytes_read', 1321043633, 132, {'metric_type':'counter', 'device_name': 'dogarchive-backend:dogarchive-2'}),
            ('haproxy.http.actconn', 1321043633, 17, {'metric_type':'counter', 'device_name': 'dogarchive-backend:dogarchive-2'}),
            ('haproxy.http.feconn', 1321043633, 0, {'metric_type':'counter', 'device_name': 'dogarchive-backend:dogarchive-2'}),
            ('haproxy.http.beconn', 1321043633, 0, {'metric_type':'counter', 'device_name': 'dogarchive-backend:dogarchive-2'}),
            ('haproxy.http.srv_conn', 1321043633, 0, {'metric_type':'counter', 'device_name': 'dogarchive-backend:dogarchive-2'}),
            ('haproxy.http.retries', 1321043633, 0, {'metric_type':'counter', 'device_name': 'dogarchive-backend:dogarchive-2'}),
            ('haproxy.http.srv_queue', 1321043633, 0, {'metric_type':'counter', 'device_name': 'dogarchive-backend:dogarchive-2'}),
            ('haproxy.http.backend_queue', 1321043633, 0, {'metric_type':'counter', 'device_name': 'dogarchive-backend:dogarchive-2'}),
            ('haproxy.http.status.200', 1321043633, 1, {'metric_type':'counter', 'device_name': 'dogarchive-backend:dogarchive-2'}),
        ],
        [
            ('haproxy.http.tq', 1321043638, 882, {'metric_type':'counter', 'device_name': 'dogweb:<STATS>'}),
            ('haproxy.http.tw', 1321043638, -1, {'metric_type':'counter', 'device_name': 'dogweb:<STATS>'}),
            ('haproxy.http.tc', 1321043638, -1, {'metric_type':'counter', 'device_name': 'dogweb:<STATS>'}),
            ('haproxy.http.tr', 1321043638, -1, {'metric_type':'counter', 'device_name': 'dogweb:<STATS>'}),
            ('haproxy.http.tt', 1321043638, 883, {'metric_type':'counter', 'device_name': 'dogweb:<STATS>'}),
            ('haproxy.http.bytes_read', 1321043638, 23485, {'metric_type':'counter', 'device_name': 'dogweb:<STATS>'}),
            ('haproxy.http.actconn', 1321043638, 16, {'metric_type':'counter', 'device_name': 'dogweb:<STATS>'}),
            ('haproxy.http.feconn', 1321043638, 16, {'metric_type':'counter', 'device_name': 'dogweb:<STATS>'}),
            ('haproxy.http.beconn', 1321043638, 0, {'metric_type':'counter', 'device_name': 'dogweb:<STATS>'}),
            ('haproxy.http.srv_conn', 1321043638, 0, {'metric_type':'counter', 'device_name': 'dogweb:<STATS>'}),
            ('haproxy.http.retries', 1321043638, 0, {'metric_type':'counter', 'device_name': 'dogweb:<STATS>'}),
            ('haproxy.http.srv_queue', 1321043638, 0, {'metric_type':'counter', 'device_name': 'dogweb:<STATS>'}),
            ('haproxy.http.backend_queue', 1321043638, 0, {'metric_type':'counter', 'device_name': 'dogweb:<STATS>'}),
            ('haproxy.http.status.200', 1321043638, 1, {'metric_type':'counter', 'device_name': 'dogweb:<STATS>'}),
        ],
        [
            ('haproxy.http.tq', 1321043642, 0, {'metric_type':'counter', 'device_name': 'public:<NOSRV>'}),
            ('haproxy.http.tw', 1321043642, -1, {'metric_type':'counter', 'device_name': 'public:<NOSRV>'}),
            ('haproxy.http.tc', 1321043642, -1, {'metric_type':'counter', 'device_name': 'public:<NOSRV>'}),
            ('haproxy.http.tr', 1321043642, -1, {'metric_type':'counter', 'device_name': 'public:<NOSRV>'}),
            ('haproxy.http.tt', 1321043642, 0, {'metric_type':'counter', 'device_name': 'public:<NOSRV>'}),
            ('haproxy.http.bytes_read', 1321043642, 126, {'metric_type':'counter', 'device_name': 'public:<NOSRV>'}),
            ('haproxy.http.actconn', 1321043642, 17, {'metric_type':'counter', 'device_name': 'public:<NOSRV>'}),
            ('haproxy.http.feconn', 1321043642, 17, {'metric_type':'counter', 'device_name': 'public:<NOSRV>'}),
            ('haproxy.http.beconn', 1321043642, 0, {'metric_type':'counter', 'device_name': 'public:<NOSRV>'}),
            ('haproxy.http.srv_conn', 1321043642, 0, {'metric_type':'counter', 'device_name': 'public:<NOSRV>'}),
            ('haproxy.http.retries', 1321043642, 0, {'metric_type':'counter', 'device_name': 'public:<NOSRV>'}),
            ('haproxy.http.srv_queue', 1321043642, 0, {'metric_type':'counter', 'device_name': 'public:<NOSRV>'}),
            ('haproxy.http.backend_queue', 1321043642, 0, {'metric_type':'counter', 'device_name': 'public:<NOSRV>'}),
            ('haproxy.http.status.302', 1321043642, 1, {'metric_type':'counter', 'device_name': 'public:<NOSRV>'}),
        ],
        None
    ]
    for i, line in enumerate(haproxy_sample.split('\n')):
        output = parse_haproxy(None, line)
        assert output == expected[i], 'line %s: %s != %s' % (i, output, expected[i])

    print "tests passed"

if __name__ == '__main__':
    test_haproxy()
