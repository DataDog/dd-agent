from checks import Check, gethostname
from fnmatch import fnmatch
import os
import time

class RRDReadException(Exception): pass

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

    def _add_stat(self, name, value, agentConfig):
        ''' For collecting stats on Cacti checks '''
        self.stats.append(
            (name, time.time(), value, {'host_name': gethostname(agentConfig)})
        )

    def _fetch_rrd_meta(self, agentConfig, whitelist):
        ''' Return a list of list of dicts with host_name, host_desc, device_name, and rrd_path '''
        def _in_whitelist(rrd):
            path = rrd.replace('<path_rra>/','')
            for p in whitelist:
                if fnmatch(path, p):
                    return True
            return False

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
            if not whitelist or _in_whitelist(rrd_path):
                if host_name in ('localhost', '127.0.0.1'):
                    host_name = gethostname(agentConfig)
                res.append({
                    'host_name': host_name,
                    'device_name': device_name or None,
                    'rrd_path': rrd_path.replace('<path_rra>', self.rrd_path)
                })

        # Collect stats
        self._add_stat('cacti.rrd.count', len(res), agentConfig)
        num_hosts = len(set([r['host_name'] for r in res]))
        self._add_stat('cacti.hosts.count', num_hosts, agentConfig)

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

    def _consolidation_funcs(self, rrd_path, rrdtool):
        ''' Determine the available consolidation functions for this rrd '''
        import rrdtool

        try:
            info = rrdtool.info(rrd_path)
        except:
            self.logger.warn("Unable to read RRD file at %s" % (rrd_path))
            raise RRDReadException(rrd_path)

        funcs = []
        for k,v in info.items():
            if k.endswith('.cf'):
                funcs.append(v)
        return funcs

    def _read_rrd(self, rrd_path, host_name, device_name):
        import rrdtool

        metrics = []
        try:
            c_funcs = self._consolidation_funcs(rrd_path, rrdtool)
        except RRDReadException:
            # Unable to read RRD file, ignore it by returning an empty list
            return []

        for c in c_funcs:
            start = self.last_ts.get('%s.%s' % (rrd_path, c), 0)
            last_ts = start

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

                    if p[k] is not None:
                        # Add the metric to our list if it's not None
                        metrics.append((m_name, ts, p[k], {'host_name': host_name, 'device_name': device_name}))
                        last_ts = (ts + interval)

            # Update the last timestamp based on the last valid metric
            self.last_ts['%s.%s' % (rrd_path, c)] = last_ts

        return metrics


    def check(self, agentConfig):
        "Check entry point"
        try:
            self.logger.debug("Cacti check start")
            if  'cacti_mysql_server' in agentConfig \
                and 'cacti_mysql_user' in agentConfig \
                and 'cacti_rrd_path' in agentConfig \
                and agentConfig['cacti_mysql_server'] != '' \
                and agentConfig['cacti_mysql_user'] != '' \
                and agentConfig['cacti_rrd_path'] != '':

                # Connect to MySQL
                try:
                    import MySQLdb
                    self.db = MySQLdb.connect(agentConfig['cacti_mysql_server'], agentConfig['cacti_mysql_user'], 
                            agentConfig.get('cacti_mysql_pass', ''), db="cacti")
                except ImportError, e:
                    self.logger.exception("Cannot import MySQLdb")
                    return False
                except MySQLdb.OperationalError:
                    self.logger.exception('MySQL connection error')
                    return False
                self.logger.debug("Connected to MySQL to fetch Cacti metadata")

                try:
                    import rrdtool
                except ImportError:
                    self.logger.exception("Cannot import rrdtool")
                    return False

                # Clear stats for this check
                self.stats = []

                # Get whitelist patterns, if available
                patterns = []
                whitelist = agentConfig.get('cacti_rrd_whitelist', None)
                if whitelist:
                    if not os.path.isfile(whitelist) or not os.access(whitelist, os.R_OK):
                        # Don't run the check if the whitelist is unavailable
                        self.logger.exception("Unable to read whitelist file at %s" % (whitelist))
                        return False

                    wl = None
                    try:
                        wl = open(whitelist)
                        for line in wl:
                            patterns.append(line.strip())
                        wl.close()
                    except:
                        self.logger.exception("Cannot open whitelist file")
                        return False

                # Fetch RRD metadata
                self.rrd_path = agentConfig['cacti_rrd_path']
                rrd_meta = self._fetch_rrd_meta(agentConfig, patterns)

                metrics = []
                for rrd in rrd_meta:
                    metrics.extend(
                        self._read_rrd(rrd['rrd_path'], rrd['host_name'], rrd['device_name'])
                    )

                self._add_stat('cacti.metrics.count', len(metrics), agentConfig)

                # Add the Cacti stats to the payload
                metrics.extend(self.stats)

                return metrics
            else:
                return False

        except:
            self.logger.exception("Cannot check Cacti")
            return False
