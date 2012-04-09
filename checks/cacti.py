from collections import defaultdict
from checks import Check, gethostname
import subprocess, os
import sys
import re
import rrdtool

class Cacti(Check):
    CFUNC_TO_AGGR = {
        'AVERAGE': 'avg',
        'MAXIMUM': 'max',
        'MINIMUM': 'min'
    }

    CACTI_TO_DD = {
        'hdd_free': 'system.disk.free',
        'hdd_used': 'system.disk.used',
        'swap_free': 'system.swap.free',
        'load_1min': 'system.load.1',
        'load_5min': 'system.load.5',
        'load_15min': 'system.load.15',
        'mem_buffers': 'system.mem.buffers',
        'proc': 'system.proc.running',
        'users': 'system.users.current',
        'mem_swap': 'system.swap.free',
        'ping': 'system.ping.latency'
    }

    def __init__(self, logger):
        Check.__init__(self, logger)
        self.db = None
        self.rrd_path = None
        self.logger = logger
        self.last_ts = {}

    def _fetch_rrd_meta(self, agentConfig):
        ''' Return a list of list of dicts with host_name, host_desc, device_name, and rrd_path '''
        c = self.db.cursor()
        c.execute("""
                SELECT
                    h.hostname as host_name,
                    dl.snmp_index as device_name,
                    dt.data_source_path as rrd_path
                FROM data_local dl
                    JOIN host h on dl.host_id = h.id
                    JOIN data_template_data dt on dt.local_data_id = dl.id
                WHERE dt.data_source_path IS NOT NULL
                AND dt.data_source_path != ''
            """)
        res = []
        for host_name, device_name, rrd_path in c.fetchall():
            if host_name in ('localhost', '127.0.0.1'):
                host_name = gethostname(agentConfig)
            res.append({
                    'host_name': host_name,
                    'device_name': device_name or None,
                    'rrd_path': rrd_path.replace('<path_rra>', self.rrd_path)
                })
        return res

    def _format_metric_name(self, m_name, cfunc):
        ''' Format a cacti metric name into a Datadog-friendly name'''
        try:
            aggr = Cacti.CFUNC_TO_AGGR[cfunc]
        except KeyError:
            aggr = cfunc.lower()

        try:
            m_name = Cacti.CACTI_TO_DD[m_name]
            if aggr != 'avg':
                m_name += '.%s' % (aggr)
            return m_name
        except KeyError:
            return "cacti.%s.%s" % (m_name.lower(), aggr)

    def _consolidation_funcs(self, rrd_path):
        ''' Determine the available consolidation functions for this rrd '''
        info = rrdtool.info(rrd_path)
        funcs = []
        for k,v in info.items():
            if k.endswith('.cf'):
                funcs.append(v)
        return funcs

    def _read_rrd(self, rrd_path, host_name, device_name):
        metrics = []
        c_funcs = self._consolidation_funcs(rrd_path)
        start = self.last_ts.get(rrd_path, 0)

        for c in c_funcs:
            try:
                fetched = rrdtool.fetch(rrd_path, c, '--start', str(start))
            except rrdtool.error:
                # Start time was out of range, return empty list
                return []

            # Extract the data
            (start_ts, end_ts, interval) = fetched[0]
            metric_names = fetched[1]
            points = fetched[2]
            for k, m_name in enumerate(metric_names):
                m_name = self._format_metric_name(m_name, c)
                for i, p in enumerate(points):
                    ts = start_ts + (i * interval)

                    # Add the metric to our list
                    metrics.append((m_name, ts, p[k], host_name, device_name))

            # Update the last timestamp
            self.last_ts[rrd_path] = end_ts
            return metrics

    def check(self, agentConfig):
        try:
            self.logger.debug("Cacti check start")
            if  'cacti_mysql_server' in agentConfig \
                and 'cacti_mysql_user' in agentConfig \
                and 'cacti_mysql_pass' in agentConfig \
                and 'cacti_rrd_path' in agentConfig \
                and agentConfig['cacti_mysql_server'] != '' \
                and agentConfig['cacti_mysql_user'] != '' \
                and agentConfig['cacti_rrd_path'] != '':

                # Connect to MySQL
                try:
                    import MySQLdb
                    self.db = MySQLdb.connect(agentConfig['cacti_mysql_server'], agentConfig['cacti_mysql_user'], 
                            agentConfig['cacti_mysql_pass'], db="cacti")
                except ImportError, e:
                    self.logger.exception("Cannot import MySQLdb")
                    return False
                except MySQLdb.OperationalError:
                    raise
                    self.logger.exception('MySQL connection error')
                    return False
                self.logger.debug("Connected to MySQL to fetch Cacti metadata")

                try:
                    import rrdtool
                except:
                    self.logger.exception("Cannot import rrdtool")
                    return False

                # Fetch RRD metadata
                self.rrd_path = agentConfig['cacti_rrd_path']
                rrd_meta = self._fetch_rrd_meta(agentConfig)

                metrics = []
                for rrd in rrd_meta:
                    metrics.extend(
                        self._read_rrd(rrd['rrd_path'], rrd['host_name'], rrd['device_name'])
                    )
                return metrics
            else:
                return False

        except:
            raise
            self.logger.exception("Cannot check Cacti")
            return False
