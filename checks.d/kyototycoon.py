import re
import urllib2
from collections import defaultdict

from checks import AgentCheck

db_stats = re.compile(r'^db_(\d)+$')
whitespace = re.compile(r'\s')

class KyotoTycoonCheck(AgentCheck):
    """Report statistics about the Kyoto Tycoon DBM-style
    database server (http://fallabs.com/kyototycoon/)
    """

    GAUGES = {
        'serv_conn_count':    'connections',
        'serv_thread_count':  'threads',
        'cnt_get':            'ops.get.hits',
        'cnt_get_misses':     'ops.get.misses',
        'cnt_set':            'ops.set.hits',
        'cnt_set_misses':     'ops.set.misses',
        'cnt_remove':         'ops.del.hits',
        'cnt_remove_misses':  'ops.del.misses',
        'repl_delay':         'replication.delay',
    }
    DB_GAUGES = {
        'count':              'records',
        'size':               'size',
    }
    TOTALS = {
        'cnt_get':            'ops.get.total',
        'cnt_get_misses':     'ops.get.total',
        'cnt_set':            'ops.set.total',
        'cnt_set_misses':     'ops.set.total',
        'cnt_remove':         'ops.get.total',
        'cnt_remove_misses':  'ops.get.total',
    }

    def check(self, instance):
        url = instance.get('report_url')
        tags = instance.get('tags', {})
        name = instance.get('name')

        # generate the formatted list of tags
        tags = ['%s:%s' % (k, v) for k, v in tags.items()]
        if name is not None:
            tags.append('instance:%s' % name)

        try:
            response = urllib2.urlopen(url)
            body = response.read()
        except:
            self.log.exception('Could not connect to Kyoto Tycoon at %s', url)
            return

        totals = defaultdict(lambda: 0)
        for line in body.split('\n'):
            if '\t' not in line:
                continue

            key, value = line.strip().split('\t', 1)
            if key in self.GAUGES:
                name = self.GAUGES[key]
                self.gauge('kyototycoon.%s' % name, int(value), tags=tags)

            elif db_stats.match(key):
                # Also produce a per-db metrics tagged with the db
                # number in addition to the default tags
                m = db_stats.match(key)
                dbnum = int(m.group(1))
                mytags = tags + ['db:%d' % dbnum]
                for part in whitespace.split(value):
                    k, v = part.split('=', 1)
                    if k in self.DB_GAUGES:
                        name = self.DB_GAUGES[k]
                        self.gauge('kyototycoon.%s' % name, int(v), tags=mytags)

            if key in self.TOTALS:
                totals[self.TOTALS[key]] += int(value)

        for key, value in totals.items():
            self.gauge('kyototycoon.%s' % key, value, tags=tags)

if __name__ == '__main__':
    check, instances = KyotoTycoonCheck.from_yaml('kyototycoon.yaml')
    for instance in instances:
        check.check(instance)
        if check.has_events():
            print 'Events: %s' % (check.get_events())
        print 'Metrics: %s'
        import pprint
        pprint.pprint(check.get_metrics())
