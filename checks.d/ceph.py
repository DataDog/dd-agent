# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

"""ceph check
Collects metrics from ceph clusters
"""

# stdlib
import os

# project
from checks import AgentCheck
from utils.subprocess_output import get_subprocess_output
from config import _is_affirmative

# third party
import simplejson as json

class Ceph(AgentCheck):
    """ Collect metrics and events from ceph """

    DEFAULT_CEPH_CMD = '/usr/bin/ceph'
    NAMESPACE = "ceph"

    def _collect_raw(self, ceph_cmd, instance):
        use_sudo = _is_affirmative(instance.get('use_sudo', False))
        ceph_args = []
        if use_sudo:
            test_sudo = os.system('setsid sudo -l < /dev/null')
            if test_sudo != 0:
                raise Exception('The dd-agent user does not have sudo access')
            ceph_args = ['sudo', ceph_cmd]
        else:
            ceph_args = [ceph_cmd]

        args = ceph_args + ['version']
        try:
            output,_,_ = get_subprocess_output(args, self.log)
        except Exception, e:
            raise Exception('Unable to run cmd=%s: %s' % (' '.join(args), str(e)))

        raw = {}
        for cmd in ('mon_status', 'status', 'df detail', 'osd pool stats', 'osd perf'):
            try:
                args = ceph_args + cmd.split() + ['-fjson']
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
            tags.append(self.NAMESPACE + '_fsid:%s' % fsid)
            tags.append(self.NAMESPACE + '_mon_state:%s' % raw['mon_status']['state'])

        return tags

    def _publish(self, raw, func, keyspec, tags):
        try:
            for k in keyspec:
                raw = raw[k]
            func(self.NAMESPACE + '.' + k, raw, tags)
        except KeyError:
            return

    def _extract_metrics(self, raw, tags):
        try:
            for osdperf in raw['osd_perf']['osd_perf_infos']:
                local_tags = tags + ['ceph_osd:osd%s' % osdperf['id']]
                self._publish(osdperf, self.gauge, ['perf_stats', 'apply_latency_ms'], local_tags)
                self._publish(osdperf, self.gauge, ['perf_stats', 'commit_latency_ms'], local_tags)
        except KeyError:
            self.log.debug('Error retrieving osdperf metrics')

        try:
            for osdinfo in raw['osd_pool_stats']:
                name = osdinfo['pool_name']
                local_tags = tags + ['ceph_pool:%s' % name]
                self._publish(osdinfo, self.gauge, ['client_io_rate', 'op_per_sec'], local_tags)
                self._publish(osdinfo, self.gauge, ['client_io_rate', 'read_bytes_sec'], local_tags)
                self._publish(osdinfo, self.gauge, ['client_io_rate', 'write_bytes_sec'], local_tags)
        except KeyError:
            self.log.debug('Error retrieving osd_pool_stats metrics')

        try:
            osdstatus = raw['status']['osdmap']['osdmap']
            self._publish(osdstatus, self.gauge, ['num_osds'], tags)
            self._publish(osdstatus, self.gauge, ['num_in_osds'], tags)
            self._publish(osdstatus, self.gauge, ['num_up_osds'], tags)
        except KeyError:
            self.log.debug('Error retrieving osdstatus metrics')

        try:
            pgstatus = raw['status']['pgmap']
            self._publish(pgstatus, self.gauge, ['num_pgs'], tags)
            for pgstate in pgstatus['pgs_by_state']:
                s_name = pgstate['state_name'].replace("+", "_")
                self.gauge(self.NAMESPACE + '.pgstate.' + s_name, pgstate['count'], tags)
        except KeyError:
            self.log.debug('Error retrieving pgstatus metrics')

        try:
            num_mons = len(raw['mon_status']['monmap']['mons'])
            self.gauge(self.NAMESPACE + '.num_mons', num_mons, tags)
        except KeyError:
            self.log.debug('Error retrieving mon_status metrics')

        try:
            stats = raw['df_detail']['stats']
            self._publish(stats, self.gauge, ['total_objects'], tags)
            used = float(stats['total_used_bytes'])
            total = float(stats['total_bytes'])
            if total > 0:
                self.gauge(self.NAMESPACE + '.aggregate_pct_used', 100.0*used/total, tags)

            l_pools = raw['df_detail']['pools']
            self.gauge(self.NAMESPACE + '.num_pools', len(l_pools), tags)
            for pdata in l_pools:
                local_tags = list(tags + [self.NAMESPACE + '_pool_name:%s' % pdata['name']])
                stats = pdata['stats']
                used = float(stats['bytes_used'])
                avail = float(stats['max_avail'])
                total = used+avail
                if total > 0:
                    self.gauge(self.NAMESPACE + '.pct_used', 100.0*used/total, local_tags)
                self.gauge(self.NAMESPACE + '.num_objects', stats['objects'], local_tags)
                self.rate(self.NAMESPACE + '.read_bytes', stats['rd_bytes'], local_tags)
                self.rate(self.NAMESPACE + '.write_bytes', stats['wr_bytes'], local_tags)

        except (KeyError, ValueError):
            self.log.debug('Error retrieving df_detail metrics')

    def _perform_service_checks(self, raw, tags):
        if 'status' in raw:
            s_status = raw['status']['health']['overall_status']
            if s_status.find('_OK') != -1:
                status = AgentCheck.OK
            else:
                status = AgentCheck.CRITICAL
            self.service_check(self.NAMESPACE + '.overall_status', status)

    def check(self, instance):
        ceph_cmd = instance.get('ceph_cmd') or self.DEFAULT_CEPH_CMD
        raw = self._collect_raw(ceph_cmd, instance)
        tags = self._extract_tags(raw, instance)
        self._extract_metrics(raw, tags)
        self._perform_service_checks(raw, tags)
