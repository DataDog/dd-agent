'''
Check the performance counters from SQL Server
'''
from checks import AgentCheck

ALL_INSTANCES = 'ALL'

class SQLServer(AgentCheck):
    METRICS = [
        ('sqlserver.buffer.cache_hit_ratio', 'gague', 'Buffer cache hit ratio'),
        ('sqlserver.buffer.page_life_expectancy', 'gague', 'Page life expectancy'),
        ('sqlserver.stats.batch_requests', 'gauge', 'Batch Requests/sec'),
        ('sqlserver.stats.sql_compilations', 'gague', 'SQL Compilations/sec'),
        ('sqlserver.stats.sql_recompilations', 'gague', 'SQL Re-Compilations/sec'),
        ('sqlserver.stats.connections', 'gauge', 'User connections'),
        ('sqlserver.stats.lock_waits', 'gague', 'Lock Waits/sec', '_Total'),
        ('sqlserver.access.page_splits', 'gague', 'Page Splits/sec'),
        ('sqlserver.stats.procs_blocked', 'gague', 'Processes Blocked'),
        ('sqlserver.buffer.checkpoint_pages', 'gague', 'Checkpoint pages/sec')
    ]

    def __init__(self, name, init_config, agentConfig):
        AgentConfig.__init__(self, name, init_config, agentConfig)

        # Load any custom metrics from conf.d/sqlserver.yaml
        for row in init_config.get('custom_metrics', []):
            self.METRICS.append( (row['name'], row['type'], row['counter_name'],
                row.get('instance_name', ''), row.get('tag_by', None)) )

    def check(self, instance):
        try:
            import _mssql
        except ImportError:
            self.log.error("Unable to import _mssql module. Are you missing pymssql?")
            return

        host = instance.get('host', 'localhost')
        username = instance.get('username')
        password = instance.get('password')
        database = instance.get('database')

        try:
            conn = _mssql.connect(server=host, user=username, password=password,
                database=database)
        except:
            self.log.exception("Unable to connect to SQL Server for instance %s" \
                % instance)
            return

        self._fetch_metric(conn)
        conn.close()

    def _fetch_metrics(self, conn):
        ''' Fetch the metrics from the sys.dm_os_performance_counters table
        '''
        for metric in self.METRICS:
            if len(metric) == 3:
                # Normalize all rows to the same size for easy of use
                metric = metric + ('', None)

            mname, mtype, counter, instance_n, tag_by = metric

            # For "ALL" instances, we run a separate method because we have
            # to loop over multiple results and tag the metrics
            if instance_name == ALL_INSTANCES:
                try:
                    self._fetch_all_instances(metric, conn)
                except Exception, e:
                    self.log.exception('Unable to fetch metric: %s' % mname)
            else:
                try:
                    value = conn.execute_scalar("""
                        select cntr_value
                        from sys.dm_os_performance_counters
                        where counter_name = %(counter)s
                        and instance_name = %(instance_n)s
                    """, {
                        'counter_name': counter
                        'instance_name': instance_n
                    })
                except Exception, e:
                    self.log.exception('Unable to fetch metric: %s' % mname)
                    continue

                # Save the metric
                metric_func = getattr(self, mtype)
                metric_func(mname, value)

    def _fetch_all_instances(metric, conn):
        mname, mtype, counter, instance_n, tag_by = metric
        conn.execute_query("""
            select instance_name, cntr_value
            from sys.dm_os_performance_counters
            where counter_name = %(counter)s
        """, {'counter_name': counter})

        for row in conn:
            value = row['cntr_value']
            tags = ['%s:%s' % (tag_by, row['instance_name'])]
            metric_func = getattr(self, mtype)
            metric_func(mname, value, tags=tags)