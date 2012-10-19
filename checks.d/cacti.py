from checks import AgentCheck

from fnmatch import fnmatch
import os

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
    'mem_buffers': 'system.mem.buffered',
    'proc': 'system.proc.running',
    'users': 'system.users.current',
    'mem_swap': 'system.swap.free',
    'ping': 'system.ping.latency'
}

class Cacti(AgentCheck):
    def __init__(self, name, init_config, agentConfig):
        AgentCheck.__init__(self, name, init_config, agentConfig)
        self.dbs = {}
        self.last_ts = {}

    def check(self, instance):
        required = ['mysql_host', 'mysql_user', 'rrd_path']
        for param in required:
            if not instance.get(param):
                self.log.warn("Cacti instance missing %s. Skipping." % (param))

        # Load the instance configuration
        host = instance.get('mysql_host')
        user = instance.get('mysql_user')
        password = instance.get('mysql_password')
        db = instance.get('mysql_db', 'cacti')
        rrd_path = instance.get('rrd_path')
        whitelist = instance.get('rrd_whitelist')

        # Generate an instance key to store state across checks
        key = _instance_key(instance)

        # The rrdtool module is required for the check to work
        try:
            import rrdtool
        except ImportError:
            self.log.exception("Cannot import rrdtool, Cacti check will not run.")
            return

        # Try importing MySQL and connecting to the database
        try:
            import MySQLdb
            self.dbs[key] = MySQLdb.connect(host, user, password, db)
        except ImportError:
            self.log.exception("Cannot import MySQLdb")
            return
        except MySQLdb.OperationalError:
            self.log.exception('MySQL connection error')
            return

        self.log.debug("Connected to MySQL to fetch Cacti metadata")

        # Get whitelist patterns, if available
        patterns = []
        if whitelist:
            if not os.path.isfile(whitelist) or not os.access(whitelist, os.R_OK):
                # Don't run the check if the whitelist is unavailable
                self.log.exception("Unable to read whitelist file at %s" \
                    % (whitelist))

            wl = None
            try:
                wl = open(whitelist)
                for line in wl:
                    patterns.append(line.strip())
                wl.close()
            except Exception:
                wl.close()
                self.log.exception("There was a problem when reading whitelist file")
                return False

        # Fetch the RRD metadata from MySQL
        db = self.dbs[key]
        rrd_meta = self._fetch_rrd_meta(db, rrd_path, patterns)

        # Load the metrics from each RRD, tracking the count as we go
        metric_count = 0
        for hostname, device_name, rrd_path in rrd_meta:
            m_count = self._read_rrd(rrd_path, hostname, device_name)
            metric_count += m_count

        self.gauge('cacti.metrics.count', metric_count)

    def _read_rrd(self, rrd_path, hostname, device_name):
        ''' Main metric fetching method '''
        import rrdtool

        try:
            info = rrdtool.info(rrd_path)
        except Exception:
            # Unable to read RRD file, ignore it
            self.log.exception("Unable to read RRD file at %s" % rrd_path)
            return

        # Find the consolidation functions for the RRD metrics
        c_funcs = [v for k,v in info.items() if k.endswith('.cf')]

        for c in c_funcs:
            start = self.last_ts.get('%s.%s' % (rrd_path, c), 0)
            last_ts = start

            try:
                fetched = rrdtool.fetch(rrd_path, c, '--start', str(start))
            except rrdtool.error:
                # Start time was out of range, skip this RRD
                self.log.warn("Time %s out of range for %s" % (rrd_path, start))
                return

            # Extract the data
            (start_ts, end_ts, interval) = fetched[0]
            metric_names = fetched[1]
            points = fetched[2]
            for k, m_name in enumerate(metric_names):
                m_name = self._format_metric_name(m_name, c)
                for i, p in enumerate(points):
                    ts = start_ts + (i * interval)

                    if p[k] is None:
                        continue

                    # Save this metric as a gauge
                    val = self._transform_metric(m_name, p[k])
                    self.gauge(m_name, ts, val, hostname=hostname,
                        device_name=device_name)
                    last_ts = (ts + interval)

            # Update the last timestamp based on the last valid metric
            self.last_ts['%s.%s' % (rrd_path, c)] = last_ts

        return metrics

    def _instance_key(*args):
        ''' return a key unique for this instance '''
        return '|'.join([str(a) for a in args])

    def _fetch_rrd_meta(self, db, rrd_path, whitelist):
        ''' Fetch metadata about each RRD in this Cacti DB, returning a list of
            tuples of (hostname, device_name, rrd_path)
        '''
        def _in_whitelist(rrd):
            path = rrd.replace('<path_rra>/','')
            for p in whitelist:
                if fnmatch(path, p):
                    return True
            return False

        c = db.cursor()

        # Check for the existence of the `host_snmp_cache` table
        res = c.execute("show tables like 'host_snmp_cache'").fetchall()
        if res:
            # Fetch the snmp device name
            rrd_query = """
                SELECT
                    h.hostname as hostname,
                    dl.snmp_index as device_name,
                    dt.data_source_path as rrd_path,
                    hsc.field_value as snmp_device_name
                FROM data_local dl
                    JOIN host h on dl.host_id = h.id
                    JOIN data_template_data dt on dt.local_data_id = dl.id
                    LEFT JOIN host_snmp_cache hsc on h.id = hsc.host_id
                        AND dl.snmp_index = hsc.snmp_index
                WHERE dt.data_source_path IS NOT NULL
                AND dt.data_source_path != ''
                AND (hsc.field_name = 'ifName' OR hsc.field_name is NULL)
            """
        else:
            rrd_query = """
                SELECT
                    h.hostname as hostname,
                    dl.snmp_index as device_name,
                    dt.data_source_path as rrd_path,
                    NULL as snmp_device_name
                FROM data_local dl
                    JOIN host h on dl.host_id = h.id
                    JOIN data_template_data dt on dt.local_data_id = dl.id
                WHERE dt.data_source_path IS NOT NULL
                AND dt.data_source_path != ''
            """

        c.execute(rrd_query)
        res = []
        for hostname, device_name, rrd_path, snmp_device_name in c.fetchall():
            if not whitelist or _in_whitelist(rrd_path):
                if hostname in ('localhost', '127.0.0.1'):
                    hostname = self.hostname
                rrd_path = rrd_path.replace('<path_rra>', rrd_path)
                device_name = snmp_device_name or device_name or None
                res.append((hostname, device_name, rrd_path))

        # Collect stats
        num_hosts = len(set([r[0] for r in res]))
        self.gauge('cacti.rrd.count', len(res))
        self.gauge('cacti.hosts.count', num_hosts)

        return res

    def _format_metric_name(self, m_name, cfunc):
        ''' Format a cacti metric name into a Datadog-friendly name '''
        try:
            aggr = CFUNC_TO_AGGR[cfunc]
        except KeyError:
            aggr = cfunc.lower()

        try:
            m_name = CACTI_TO_DD[m_name]
            if aggr != 'avg':
                m_name += '.%s' % (aggr)
            return m_name
        except KeyError:
            return "cacti.%s.%s" % (m_name.lower(), aggr)

    def _transform_metric(self, m_name, val):
        ''' Add any special case transformations here '''
        # Report memory in MB
        if m_name[0:11] in ('system.mem.', 'system.disk'):
            return val / 1024
        return val


    '''
        For backwards compatability with pre-checks.d configuration.
        Convert old-style config to new-style config.
    '''
    @staticmethod
    def parse_agent_config(agentConfig):
        required = ['cacti_mysql_server', 'cacti_mysql_user', 'cacti_rrd_path']
        for param in required:
            if not agentConfig.get(param):
                return False

        return {
            'instances': [{
                'mysql_host': agentConfig.get('cacti_mysql_server'),
                'mysql_user': agentConfig.get('cacti_mysql_user'),
                'mysql_password': agentConfig.get('cacti_mysql_password'),
                'rrd_path': agentConfig.get('cacti_rrd_path'),
                'rrd_whitelist': agentConfig.get('cacti_rrd_whitelist')
            }]
        }