from collections import defaultdict
from checks import Check
import subprocess, os
import sys
import re

class Cacti(Check):
    def __init__(self, logger):
        Check.__init__(self, logger)
        self.db = None
        self.rrd_path = None
        self.logger = logger
        self.last_ts = {}

    def _fetch_rrd_meta(self):
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
            res.append({
                    'host_name': host_name,
                    'device_name': device_name,
                    'rrd_path': rrd_path.replace('<path_rra>', self.rrd_path)
                })
        return res

    def _format_metric_name(self):
        ''' Format a cacti metric name into a Datadog-friendly name'''
        pass

    def _consolidation_funcs(self, rrd_path):
        ''' Determine the available consolidation functions for this rrd '''
        info = rrdtool.info(rrd_path)
        funcs = []
        for k,v in info.items():
            if k.endswith('.cf'):
                funcs.append(v)
        return funcs

    def _write_metric(self, cacti_name, ts, val, host_name, device_name):
        metric_name = self._format_metric_name(cacti_name)
        
        # Register the metric, if needed
        if not self.is_metric(metric_name):
            self.gauge(metric)

        # FIXME: How can we support host_name and device_name in save_sample? Use something else?
        self.save_sample(metric_name, val, ts)

    def _read_rrd(self, rrd_path, host_name, device_name):
        c_funcs = self._consolidation_funcs(rrd_path)
        start = self.last_ts.get(rrd_path, 0)

        for c in c_funcs:
            try:
                fetch = rrdtool.fetch(rrd_path, c, '--start', start)
            except rrdtool.error:
                # Start time was out of range
                return

            # Extract the data
            (start_ts, end_ts, interval) = fetched[0]
            metric_names = fetched[1]
            points = fetched[2]

            for p, i in enumerate(points):
                ts = start_ts + (i * interval)
                for m_name, k in enumerate(metric_names):
                    # Write a metric with ts for each 
                    self._write_metric(m_name, ts, p[k], host_name, device_name)

            # Update the last timestamp
            self.last_ts[rrd_path] = end_ts

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
                rrd_meta = self._fetch_rrd_meta()

                for rrd in rrd_meta:
                    self._read_rrd(rrd['rrd_path'], rrd['host_name'], rrd['device_name'])

            else:
                return False

        except:
            raise
            self.logger.exception("Cannot check Cacti")
            return False
