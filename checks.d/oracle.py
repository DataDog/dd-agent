from checks import AgentCheck

import cx_Oracle

class Oracle(AgentCheck):
    SERVICE_CHECK_NAME = 'oracle.can_connect'
    SYS_METRICS = {
        'Buffer Cache Hit Ratio':           'oracle.buffer_cachehit_ratio', 
        'Cursor Cache Hit Ratio':           'oracle.cursor_cachehit_ratio', 
        'Library Cache Hit Ratio':          'oracle.library_cachehit_ratio', 
        'Shared Pool Free %':               'oracle.shared_pool_free', 
        'Physical Reads Per Sec':           'oracle.physical_reads', 
        'Physical Writes Per Sec':          'oracle.physical_writes', 
        'Enqueue Timeouts Per Sec':         'oracle.enqueue_timeouts', 
        'GC CR Block Received Per Second':  'oracle.gc_cr_receive_time', 
        'Global Cache Blocks Corrupted':    'oracle.cache_blocks_corrupt', 
        'Global Cache Blocks Lost':         'oracle.cache_blocks_lost', 
        'Logons Per Sec':                   'oracle.logons', 
        'Average Active Sessions':          'oracle.active_sessions', 
        'Long Table Scans Per Sec':         'oracle.long_table_scans', 
        'SQL Service Response Time':        'oracle.service_response_time', 
        'User Rollbacks Per Sec':           'oracle.user_rollbacks', 
        'Total Sorts Per User Call':        'oracle.sorts_per_user_call', 
        'Rows Per Sort':                    'oracle.rows_per_sort', 
        'Disk Sort Per Sec':                'oracle.disk_sorts',
        'Memory Sorts Ratio':               'oracle.memroy_sorts_ratio',
        'Database Wait Time Ratio':         'oracle.database_wait_time_ratio',
        'Enqueue Timeouts Per Sec':         'oracle.enqueue_timeouts',
        'Session Limit %':                  'oracle.session_limit_usage',
        'Session Count':                    'oracle.session_count',
        'Temp Space Used':                  'oracle.temp_space_used',
    }

    def check(self, instance):
        self.log.debug('Running cx_Oracle version {0}'.format(cx_Oracle.version))
        server, user, password, tags = self._get_config(instance)

        if not server or not user:
            raise Exception("Oracle host and user are needed")

        con = self._get_connection(server, user, password)

        self._get_sys_metrics(con)

        self._get_tablespace_metrics(con)        

    def _get_config(self, instance):
        self.server = instance.get('server', None)
        user = instance.get('user', None)
        password = instance.get('password', None)
        tags = instance.get('tags', None)
        return (self.server, user, password, tags)

    def _get_connection(self, server, user, password):
        self.service_check_tags = [
            'server:%s' % server
        ]
        connect_string = '{0}/{1}@{2}'.format(user, password, server)
        try:
            con = cx_Oracle.connect(connect_string)
            self.log.debug("Connected to Oracle DB")
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.OK,
                               tags=self.service_check_tags)
        except Exception, e:
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL,
                               tags=self.service_check_tags)
            self.log.error(e)
            raise
        return con

    def _get_sys_metrics(self, con):
        query = "SELECT METRIC_NAME, VALUE, BEGIN_TIME FROM GV$SYSMETRIC " \
            "ORDER BY BEGIN_TIME"
        cur = con.cursor()
        cur.execute(query)       
        for row in cur:
            metric_name = row[0]
            metric_value = row[1]
            if metric_name in self.SYS_METRICS:
                self.gauge(self.SYS_METRICS[metric_name], metric_value)

    def _get_tablespace_metrics(self, con):
        query = "SELECT TABLESPACE_NAME, USED_SPACE, TABLESPACE_SIZE, USED_PERCENT " \
            "FROM DBA_TABLESPACE_USAGE_METRICS"
        cur = con.cursor()
        cur.execute(query)
        for row in cur:
            tablespace_tag = 'tablespace:%s' % row[0]
            used = row[1]
            size = row[2]
            in_use = row[3]
            self.gauge('oracle.tablespace.used', used, tags=[tablespace_tag])
            self.gauge('oracle.tablespace.size', size, tags=[tablespace_tag])
            self.gauge('oracle.tablespace.in_use', in_use, tags=[tablespace_tag])
