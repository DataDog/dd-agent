"""ceph check
Collects metrics from ceph clusters
"""

# stdlib
import os
import json

# project
from checks import AgentCheck

NAMESPACE = "ceph"

class Ceph(AgentCheck):
    """ Collect metrics and events from ceph """

    def __init__(self, name, init_config, agentConfig, instances=None):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances)

    def _run_command(self, cmd):
        fd = os.popen(cmd)
        raw = fd.read()
        fd.close()
        return json.loads(raw)
    
    def _collect_raw(self):
        raw = {}
        for cmd in ( 'mon_status', 'status', 'df detail', 'osd pool stats', 'osd perf', 'pg dump',
                     'pg ls', 'pg dump_json all' ):
            try:
                res = self._run_command("ceph %s -f json 2>/dev/null" % cmd)
            except Exception, e:
                self.log.warning('Unable to parse data from cmd=%s: %s' % (cmd, str(e)))
                continue
            
            name = cmd.replace(' ', '_')
            raw[name] = res

        return raw

    def _extract_tags(self, raw):
        tags = []
        if 'mon_status' in raw:
            tags.append(NAMESPACE + '_fsid:%s' % raw['mon_status']['monmap']['fsid'])
            tags.append(NAMESPACE + '_mon_state:%s' % raw['mon_status']['state'])
        self.tags = tags
        
    def _extract_metrics(self, raw):
        if 'mon_status' in raw:
            num_mons = len(raw['mon_status']['monmap']['mons'])
            self.gauge(NAMESPACE + '.num_mons', num_mons, self.tags)

        if 'df_detail' in raw:
            stats = raw['df_detail']['stats']
            print stats
            self.gauge(NAMESPACE + '.total_objects', stats['total_objects'], self.tags)
            used = float(stats['total_used_bytes'])
            avail = float(stats['total_avail_bytes'])
            if avail>0:
                self.gauge(NAMESPACE + '.aggregate_used', used/avail, self.tags)

            l_pools = raw['df_detail']['pools']
            self.gauge(NAMESPACE + '.num_pools', len(l_pools), self.tags)
            for pdata in l_pools:                
                tags = list(self.tags + [ NAMESPACE + '_pool_name:%s' % pdata['name'] ])
                stats = pdata['stats']
                used = float(stats['bytes_used'])
                avail = float(stats['max_avail'])
                if avail>0:
                    self.gauge(NAMESPACE + '.used', used/avail, tags)
                self.gauge(NAMESPACE + '.num_objects', stats['objects'], tags)
                self.gauge(NAMESPACE + '.rd_bytes', stats['rd_bytes'], tags)
                self.gauge(NAMESPACE + '.wr_bytes', stats['wr_bytes'], tags)

    def _perform_service_checks(self, raw):
        if 'status' in raw:
            s_status = raw['status']['health']['overall_status']
            if s_status.find('_OK')!=-1:
                status = AgentCheck.OK
            else:
                status = AgentCheck.CRITICAL
            self.service_check(NAMESPACE + '.overall_status', status)

    def check(self, instance):
        raw = self._collect_raw()
        self._extract_tags(raw)
        if instance.get('enable_metrics', True):
            self._extract_metrics(raw)
        if instance.get('enable_service_checks', True):
            self._perform_service_checks(raw)

        
