from checks.jmx_connector import JmxCheck, JMXMetric
import re


first_cap_re = re.compile('(.)([A-Z][a-z]+)')
all_cap_re = re.compile('([a-z0-9])([A-Z])')

def convert(name):
    """Convert from CamelCase to camel_case"""

    s1 = first_cap_re.sub(r'\1_\2', name)
    return all_cap_re.sub(r'\1_\2', s1).lower()

class CassandraMetric(JMXMetric):
    BLACKLIST = ['pendingTasks', 
    'MinimumCompactionThreshold',
    'RowCacheKeysToSave',
    'MaximumCompactionThreshold',
    'KeyCacheSavePeriodInSeconds',
    'RowCacheSavePeriodInSeconds',
    ]

    @property
    def send_metric(self):
        if self.tags.get('keyspace', "") == "system":
            return False

        if self.attribute_name in CassandraMetric.BLACKLIST:
            return False

        return True

    @property
    def metric_name(self):
        return ".".join(self.domain.split('.')[2:]+[convert(self.attribute_name)])

    @property
    def type(self):
        return "gauge"


class Cassandra(JmxCheck):

    CASSANDRA_DOMAINS = ['org.apache.cassandra.db',
                        'org.apache.cassandra.internal',
                        'org.apache.cassandra.net',
                        'org.apache.cassandra.request'
                        ]


    def check(self, instance):
        (host, port, user, password, jmx, instance_name) = self._load_config(instance)
        tags = {}
        if instance_name is not None:
            tags['instance'] = instance_name
        dump = jmx.dump()

        self.get_and_send_jvm_metrics(instance, dump, tags)

        self.create_metrics(instance, self.get_beans(dump, Cassandra.CASSANDRA_DOMAINS), CassandraMetric, tags=tags)

        metrics = []
        for m in self.get_jmx_metrics():
            m.filter_tags(keys_to_remove=['columnfamily'],
                        values_to_remove=['ColumnFamilies'])
            metrics.append(m)

        self.set_jmx_metrics(metrics)

        self.send_jmx_metrics()
        self.clear_jmx_metrics()
