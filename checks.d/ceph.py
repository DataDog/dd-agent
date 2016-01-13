"""ceph check
Collects metrics from ceph clusters
"""

# stdlib
import os
import json

# project
from checks import AgentCheck
from utils.subprocess_output import get_subprocess_output
from config import _is_affirmative

NAMESPACE = "ceph"

class Ceph(AgentCheck):
    """ Collect metrics and events from ceph """

    DEFAULT_CEPH_CMD = '/usr/bin/ceph'

    def __init__(self, name, init_config, agentConfig, instances=None):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances)

    def _run_command(self, cmd):
        fd = os.popen(cmd)
        raw = fd.read()
        fd.close()
        return json.loads(raw)

    def _collect_raw(self, ceph_cmd, instance):
        use_sudo = _is_affirmative(instance.get('use_sudo', False))
        if use_sudo:
            test_sudo = os.system('setsid sudo -l < /dev/null')
            if test_sudo != 0:
                raise Exception('The dd-agent user does not have sudo access')

        raw = {}
        for cmd in ('mon_status', 'status', 'df detail', 'osd pool stats', 'osd perf'):
            try:
                if use_sudo:
                    args = ['sudo', ceph_cmd]
                else:
                    args = [ceph_cmd]
                args.extend(cmd.split())
                args.append('-fjson')
                output,_,_ = get_subprocess_output(args, self.log)
                res = json.loads(output)
            except Exception, e:
                self.log.warning('Unable to parse data from cmd=%s: %s' % (cmd, str(e)))
                continue

            name = cmd.replace(' ', '_')
            raw[name] = res

        return raw

    def _extract_tags(self, raw, instance):
        tags = instance.get('tags', [])
        if 'mon_status' in raw:
            fsid = raw['mon_status']['monmap']['fsid']
            tags.append(NAMESPACE + '_fsid:%s' % fsid)
            tags.append(NAMESPACE + '_mon_state:%s' % raw['mon_status']['state'])

        name = instance.get('name', None)
        if name:
            tags.append(NAMESPACE + '_name:%s' % name)

        self.tags = tags

    def _extract_metrics(self, raw):
        if 'osd_perf' in raw:
            for osdperf in raw['osd_perf']['osd_perf_infos']:
                tags = self.tags + ['ceph_osd:osd%s' % osdperf['id']]
                for k,v in osdperf['perf_stats'].iteritems():
                    self.gauge(NAMESPACE + '.' + k, v, tags)

        if 'osd_pool_stats' in raw:
            for osdinfo in raw['osd_pool_stats']:
                name = osdinfo['pool_name']
                tags = self.tags + ['ceph_pool:%s' % name]
                for k,v in osdinfo['client_io_rate'].iteritems():
                    self.gauge(NAMESPACE + '.' + k, v, tags)

        if 'status' in raw:
            osdstatus = raw['status']['osdmap']['osdmap']
            self.gauge(NAMESPACE + '.num_osds', osdstatus['num_osds'], self.tags)
            self.gauge(NAMESPACE + '.num_in_osds', osdstatus['num_in_osds'], self.tags)
            self.gauge(NAMESPACE + '.num_up_osds', osdstatus['num_up_osds'], self.tags)

            pgstatus = raw['status']['pgmap']
            self.gauge(NAMESPACE + '.num_pgs', pgstatus['num_pgs'], self.tags)
            for pgstate in pgstatus['pgs_by_state']:
                s_name = pgstate['state_name'].replace("+", "_")
                self.gauge(NAMESPACE + '.pgstate.' + s_name, pgstate['count'], self.tags)

        if 'mon_status' in raw:
            num_mons = len(raw['mon_status']['monmap']['mons'])
            self.gauge(NAMESPACE + '.num_mons', num_mons, self.tags)

        if 'df_detail' in raw:
            stats = raw['df_detail']['stats']
            self.gauge(NAMESPACE + '.total_objects', stats['total_objects'], self.tags)
            used = float(stats['total_used_bytes'])
            avail = float(stats['total_avail_bytes'])
            if avail > 0:
                self.gauge(NAMESPACE + '.aggregate_pct_used', 100.0*used/avail, self.tags)

            l_pools = raw['df_detail']['pools']
            self.gauge(NAMESPACE + '.num_pools', len(l_pools), self.tags)
            for pdata in l_pools:
                tags = list(self.tags + [NAMESPACE + '_pool_name:%s' % pdata['name']])
                stats = pdata['stats']
                used = float(stats['bytes_used'])
                avail = float(stats['max_avail'])
                if avail > 0:
                    self.gauge(NAMESPACE + '.pct_used', 100.0*used/avail, tags)
                self.gauge(NAMESPACE + '.num_objects', stats['objects'], tags)
                self.rate(NAMESPACE + '.rd_bytes', stats['rd_bytes'], tags)
                self.rate(NAMESPACE + '.wr_bytes', stats['wr_bytes'], tags)

    def _perform_service_checks(self, raw):
        if 'status' in raw:
            s_status = raw['status']['health']['overall_status']
            if s_status.find('_OK') != -1:
                status = AgentCheck.OK
            else:
                status = AgentCheck.CRITICAL
            self.service_check(NAMESPACE + '.overall_status', status)

    def check(self, instance):
        ceph_cmd = instance.get('ceph_cmd', self.DEFAULT_CEPH_CMD)
        raw = self._collect_raw(ceph_cmd, instance)
        self._extract_tags(raw, instance)
        if instance.get('publish_metrics', True):
            self._extract_metrics(raw)
        if instance.get('publish_service_checks', True):
            self._perform_service_checks(raw)
