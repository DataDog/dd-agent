from checks import AgentCheck


class HDFSCheck(AgentCheck):
    """Report on free space and space used in HDFS.
    """

    def check(self, instance):
        try:
            import snakebite.client
        except ImportError:
            raise ImportError('HDFSCheck requires the snakebite module')

        if 'namenode' not in instance:
            raise ValueError('Missing key \'namenode\' in HDFSCheck config')

        hostport = instance['namenode']
        if ':' in hostport:
            host, _, port = hostport.partition(':')
            port = int(port)
        else:
            host = hostport
            port = 8020

        hdfs = snakebite.client.Client(host, port)
        stats = hdfs.df()
        # {'used': 2190859321781L,
        #  'capacity': 76890897326080L,
        #  'under_replicated': 0L,
        #  'missing_blocks': 0L,
        #  'filesystem': 'hdfs://hostname:port',
        #  'remaining': 71186818453504L,
        #  'corrupt_blocks': 0L}

        self.gauge('hdfs.used', stats['used'])
        self.gauge('hdfs.free', stats['remaining'])
        self.gauge('hdfs.capacity', stats['capacity'])
        self.gauge('hdfs.in_use', float(stats['used']) / float(stats['capacity']))
        self.gauge('hdfs.under_replicated', stats['under_replicated'])
        self.gauge('hdfs.missing_blocks', stats['missing_blocks'])
        self.gauge('hdfs.corrupt_blocks', stats['corrupt_blocks'])

if __name__ == '__main__':
    check, instances = HDFSCheck.from_yaml('./hdfs.yaml')
    for instance in instances:
        check.check(instance)
        print "Events: %r" % check.get_events()
        print "Metrics: %r" % check.get_metrics()

