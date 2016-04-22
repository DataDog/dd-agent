from checks import AgentCheck

import cx_Oracle

class Oracle(AgentCheck):
    SERVICE_CHECK_NAME = 'oracle.can_connect'
    SYS_METRICS = {
      'Average Active Sessions': 'oracle.active_sessions.avg',
        'Current Logons Count': 'oracle.current_logons',
        'Current Open Cursors Count': 'oracle.current_open_cursors',
        'Executions Per User Call': 'oracle.executions_per_user_call',
        'Host CPU Usage Per Sec': 'oracle.cpu.usage_per_sec',
        'Host CPU Usage Per Txn': 'oracle.transaction_cpu_usage',
        'Executions Per Sec': 'oracle.executions_per_sec',
        'Executions Per Txn': 'oracle.executions_per_transaction',
        'Full Index Scans Per Sec': 'oracle.index.scans_per_sec',
        'Full Index Scans Per Txn': 'oracle.index.scans_per_txn',
        'I/O Megabytes per Second': 'oracle.io.megabytes_per_s',
        'I/O Requests per Second': 'oracle.io.requests_per_s',
        'Memory Sorts Ratio': 'oracle.memory_sorts_ratio',
        'Physical Read Bytes Per Sec': 'oracle.physical_reads_per_s',
        'Physical Write Bytes Per Sec': 'oracle.physical_writes_per_s'
    }

    def check(self, instance):
        self.log.debug('Running cx_Oracle version {0}'.format(cx_Oracle.version))
        server, user, password, tags = self._get_config(instance)

        if not server or not user:
            raise Exception("Oracle host and user are needed")

        con = self._get_connection(server, user, password)

        cur = self._run_query(con)

        self._submit_metrics(cur)        

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
        connect_string = '{0}/{1}@{2}'.format(user,password,server)
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

    def _run_query(self, con):
        query = "SELECT METRIC_NAME, VALUE, BEGIN_TIME FROM GV$SYSMETRIC " \
            "ORDER BY BEGIN_TIME"
        cur = con.cursor()
  cur.execute(query)       
        return cur

    def _submit_metrics(self, cur):
        for row in cur:
            metric_name = row[0]
            metric_value = row[1]
            if metric_name in self.SYS_METRICS:
                self.gauge(self.SYS_METRICS[metric_name], metric_value)

