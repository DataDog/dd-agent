"""HAProxy log parser

Parses every single line of an HAProxy log to extract metrics that are not captured
from the admin interface (timings, response code, query size).

By default, each log is going to create 9-10 data points per line.

Each metric is tagged with:

* service:backend_name
* cmd:(get/post/put/delete)

Optionally the parser can match the URL parameter of each line against a list
of regular expressions to apply additional tags. That list of regex is passed
to the parser constructor as a dictionary named `url_tags`.

Example of url_tags:

{
    r"^/help": "help,public",
    r"^/private": "private",
    r"^/api/v1/metric": "api, metric"
}

will yield the following tags when presented with URLs:

* /help/abc?yes  => ["help", "public"]
* /private       => ["private"]
* /api/v1/metric => ["api", "metric"]
* /download      => None
* /privat        => None 

The more URL regexes there are, the slower parsing will be. To get of parsing
you can edit the sample url_tags at the end of the file in the parser constructor and run:

cat my_haproxy_log | python dogstream/haproxy.py > /dev/null

to get a short code profile. If you see _sre.match taking a lot of cumulative time
it is a sign that the URL matching is too slow.

Log format (from section 8.2.3 of http://haproxy.1wt.eu/download/1.3/doc/configuration.txt):

  Field   Format                                Extract from the example above
      1   process_name '[' pid ']:'                            haproxy[14389]:
      2   client_ip ':' client_port                             10.0.1.2:33317
      3   '[' accept_date ']'                       [06/Feb/2009:12:14:14.655]
      4   frontend_name                                                http-in
      5   backend_name '/' server_name                             static/srv1
      6   Tq '/' Tw '/' Tc '/' Tr '/' Tt*                       10/0/30/69/109 <--- datadog gauges
      7   status_code                                                      200 <--- datadog counters
      8   bytes_read*                                                     2750 <--- datadog gauge
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

HAPROXY_RE = re.compile("^.*haproxy\[(?P<pid>\d+)\]: (?P<client_ip>[\d.]+):(?P<client_port>\d+) \[(?P<accept_date>[^]]+)\] (?P<frontend_name>\S+) (?P<backend_name>\S+)/(?P<server_name>\S+) (?P<tq>-?\d+)/(?P<tw>-?\d+)/(?P<tc>-?\d+)/(?P<tr>-?\d+)/(?P<tt>-?\d+) (?P<status_code>\d{3}) (?P<bytes_read>\d+) . . .... (?P<actconn>\d+)/(?P<feconn>\d+)/(?P<beconn>\d+)/(?P<srvconn>\d+)/(?P<retries>\d+) (?P<srv_queue>\d+)/(?P<backend_queue>\d+).*\"(?P<cmd>\w+) (?P<url>\S+) HTTP/.\..\"$")

NO_TAG = ()

class HAProxyLogParser(object):
    def __init__(self, config):
        self._logger = logging.getLogger('haproxy-logparser')
        self._state = {}
        # per tag status code counter
        self._state['codes'] = {NO_TAG: {'2xx': 0, '3xx': 0, '4xx': 0, '5xx': 0}}
        self._state['aborts'] = 0

        # Maps url regex to one or more tags
        # { url_regex: ("tag1", "tag2"), ...}
        patterns = config.get('url_tags', {})
        self._tags = {}
        try:
            for p, tags in patterns.items():
                # compile the regex and turn the tag or tags into a list of tags
                self._tags[re.compile(p)] = ["url:%s" % t.strip() for t in tags.split(",")]
        except:
            # if we fail, log and don't tag anything
            self._logger.warn("Cannot parse url patterns to tag URLs. Won't tag any URL.", exc_info = True)
            self._tags = {}

    @staticmethod
    def parse_timestamp(timestamp):
        return time.mktime(datetime.strptime(timestamp, '%d/%b/%Y:%H:%M:%S.%f').timetuple())

    def parse_status_code(self, code, lbound, ubound, metric, url_tags):
        assert lbound < ubound
        assert url_tags is None or type(url_tags) == type(())
        if int(code) >= lbound and int(code) <= ubound:
            if url_tags is not None and len(url_tags) > 0:
                if url_tags not in self._state['codes']:
                    self._state['codes'][url_tags] = {'2xx': 0, '3xx': 0, '4xx': 0, '5xx': 0}
                self._state['codes'][url_tags][metric] += 1
            else:
                self._state['codes'][NO_TAG][metric] += 1

    def map_tag(self, url):
        """Find the corresponding tag(s) based on a given url
        If no tag is found, NO_TAG (empty tuple) is returned
        """
        try:
            if url is None or len(url) == "":
                return NO_TAG
            # Regex everything
            for r in self._tags:
                if r.match(url):
                    return tuple(self._tags.get(r))
            return NO_TAG
        except:
            return NO_TAG

    def parse_line(self, line):
        points = []

        m = HAPROXY_RE.match(line)
        # No match? skip
        if m is None:
            return None

        timestamp = HAProxyLogParser.parse_timestamp(m.group('accept_date'))
        # Skip STATS call
        if m.group('server_name') == '<STATS>':
            return None

        # attributes['tags'] always exists and contains the backend_name
        # and the HTTP verb
        attributes = {'tags': ['service:%s' % m.group('backend_name'),
                               'cmd:%s' % m.group('cmd').lower()]}
        url_tags = self.map_tag(m.group('url'))
        if url_tags and url_tags != NO_TAG and len(url_tags) > 0:
            # lookup tags based on url stem
            attributes['tags'].extend(url_tags)

        # status codes
        self.parse_status_code(m.group('status_code'), 200, 299, '2xx', url_tags)
        self.parse_status_code(m.group('status_code'), 300, 399, '3xx', url_tags)
        self.parse_status_code(m.group('status_code'), 400, 499, '4xx', url_tags)
        self.parse_status_code(m.group('status_code'), 500, 599, '5xx', url_tags)

        metrics = [
            ('haproxy.http.tq', 'gauge', lambda d: int(d.group('tq'))),
            ('haproxy.http.tw', 'gauge', lambda d: int(d.group('tw'))),
            ('haproxy.http.tc', 'gauge', lambda d: int(d.group('tc'))),
            ('haproxy.http.tr', 'gauge', lambda d: int(d.group('tr'))),
            ('haproxy.http.tt', 'gauge', lambda d: int(d.group('tt'))),
            ('haproxy.http.bytes_read', 'gauge', lambda d: d.group('bytes_read')),
            ('haproxy.http.2xx', 'counter', lambda m, s=self._state, t=url_tags: s['codes'][t]['2xx']),
            ('haproxy.http.3xx', 'counter', lambda m, s=self._state, t=url_tags: s['codes'][t]['3xx']),
            ('haproxy.http.4xx', 'counter', lambda m, s=self._state, t=url_tags: s['codes'][t]['4xx']),
            ('haproxy.http.5xx', 'counter', lambda m, s=self._state, t=url_tags: s['codes'][t]['5xx']),
        ]

        def counter(d):
            "Update attributes dictionary to add counter type"
            new_d = d.copy()
            new_d['metric_type'] = 'counter'
            return new_d

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
                        self._state['aborts'] += 1
                        points.append(('haproxy.http.abort', timestamp, self._state['aborts'], counter(attributes)))
                        is_abort = True
                else:
                    if typ == 'gauge':
                        points.append((name, timestamp, value, attributes))
                    else:
                        points.append((name, timestamp, value, counter(attributes)))
        return points

if __name__ == '__main__':
    # Parse stdin and extract metrics
    import sys
    import tempfile
    import cProfile
    from pstats import Stats
    logging.basicConfig(format="%(asctime)s %(levelname)s %(filename)s:%(lineno)d %(message)s")
    def loop():
        parser = HAProxyLogParser({'url_tags': {r'^/api/v1/metric': "metric",
                                                r'/admin?stats': "stats, admin",
                                                r'^/status/sobotka': "status, sobotka"}})
        while True:
            line = sys.stdin.readline()
            if line is None or len(line) == 0:
                break
            else:
                r = parser.parse_line(line)
                if r is not None:
                    print(r)
    tmp = tempfile.NamedTemporaryFile()
    cProfile.run('loop()', tmp.name)
    try:
        Stats(tmp.name, stream=sys.stderr).sort_stats('cumulative').print_stats(40)
    except:
        Stats(tmp.name).sort_stats('cumulative').print_stats(40)

