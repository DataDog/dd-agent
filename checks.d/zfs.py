'''
ZFS check
'''
from __future__ import division

# stdlib
import subprocess
import re

# project
from checks import AgentCheck

class Zfs(AgentCheck):
    # Inject dependency so that we can make mocks work in UnitTests
    subprocess = subprocess

    ZFS_NAMESPACE = 'system.zfs.'
    ZFS_AVAILABLE = 'available'
    ZFS_USED = 'used'
    ZFS_COMPRESSRATIO = 'compressratio'

    ZPOOL_NAMESPACE = 'zpool.'
    ZPOOL_VDEV_NAMESPACE = 'zpool.vdev.'
    ZPOOL_CAPACITY = 'capacity'
    ZPOOL_SIZE = 'size'
    ZPOOL_DEDUPRATIO = 'dedupratio'
    ZPOOL_FREE = 'free'
    ZPOOL_ALLOCATED = 'allocated'
    ZPOOL_HEALTH = 'health'
    ZPOOL_TOTAL = 'total'

    zfs_metrics = [
        ZFS_AVAILABLE,
        ZFS_USED,
        ZFS_COMPRESSRATIO
    ]

    zpool_metrics = [
        ZPOOL_CAPACITY,
        ZPOOL_SIZE,
        ZPOOL_DEDUPRATIO,
        ZPOOL_FREE,
        ZPOOL_ALLOCATED
    ]

    zpool_service_checks = [
        ZPOOL_HEALTH
    ]

    def check(self, instance):
        # Retrieve the list of ZFS filesystems
        self.log.debug('Getting list of zfs filesystems')
        zfs_filesystems = self._get_zfs_filesystems()

        # Retrieve the list of Zpools
        self.log.debug('Getting list of zpools')
        zpools = self._get_zpools()

        # For each zfs filesystem, retrieve statistics and send them to datadog
        for zfs_fs in zfs_filesystems:
            self.log.debug('Reporting on ZFS filesystem {}'.format(zfs_fs))
            stats = self._get_zfs_stats(zfs_fs)
            self._process_zfs_usage(zfs_name=zfs_fs, zfs_stats=stats)

        # For each zpool, retrieve statistics and send them to datadog
        for zpool in zpools:
            self.log.debug('Reporting on zpool {}'.format(zpool))
            stats = self._get_zpool_stats(zpool)
            checks = self._get_zpool_checks(zpool)
            vdev_stats = self._get_zpool_iostat(zpool)
            self._process_zpool(zpool, stats, checks, vdev_stats)

    def _process_zpool(self, zpool, zpool_metrics, zpool_checks, zpool_vdev_stats):
        """
        Process zpool usage

        :param zpool: Name of zfs filesystem
        :param zpool_metrics: Associated statistics
        :param zpool_checks: Associated service checks
        :return: None
        """
        tags = [
            'zpool_name:{}'.format(zpool)
        ]

        for metric in zpool_metrics.keys():
            self.gauge(Zfs.ZPOOL_NAMESPACE + metric, zpool_metrics[metric], tags=tags)

        for check in zpool_checks.keys():
            if check == Zfs.ZPOOL_HEALTH:
                check_status = None
                health_status = zpool_checks[check]
                if health_status == 'ONLINE':
                    check_status = AgentCheck.OK
                elif check_status == 'DEGRADED':
                    check_status = AgentCheck.WARNING
                else:
                    check_status = AgentCheck.CRITICAL
                self.service_check(Zfs.ZPOOL_NAMESPACE + check, check_status, tags=tags, message=health_status)

        for vdev in zpool_vdev_stats:
            tags = [
                'zpool_name:{}'.format(zpool),
                'vdev_name:{}'.format(vdev)
            ]
            self.gauge(Zfs.ZPOOL_VDEV_NAMESPACE + 'total', zpool_vdev_stats[vdev]['total'], tags=tags)
            self.gauge(Zfs.ZPOOL_VDEV_NAMESPACE + 'free', zpool_vdev_stats[vdev]['free'], tags=tags)
            self.gauge(Zfs.ZPOOL_VDEV_NAMESPACE + 'percent_used', zpool_vdev_stats[vdev]['percent_used'], tags=tags)

    def _get_zpools(self):
        """
        Get list of zpools
        :return: List of zpools
        """
        p = self.subprocess.Popen(
            'sudo zpool list -H -o name'.split(),
            stdout=self.subprocess.PIPE
            )
        zpools, err = p.communicate()
        return filter(None, zpools.split('\n'))

    def _get_zpool_stats(self, zpool):
        """
        Retrieve numerical statistics about zpool.  Parses out all non-digits

        :param zpool:
        :return:
        """
        p = self.subprocess.Popen(
            'sudo zpool get {props} {name}'.format(
                props=','.join(Zfs.zpool_metrics),
                name=zpool
            ).split(),
            stdout=self.subprocess.PIPE
            )
        zpool_output, err = p.communicate()
        stats = {}
        for line in filter(None, zpool_output.split('\n')):
            properties = line.split()
            result = properties[2]
            # Stupid zpool command doesn't let you skip headers.  Toss this record
            if result == 'VALUE':
                continue
            if re.match('^\d+[K,M,G,T]', result) or re.match('^\d+\.\d+[K,M,G,T]', result):
                result = self._convert_human_to_bytes(result)
            stats[properties[1]] = re.sub('[^0-9,\.]', "", str(result))
        return stats

    def _get_zpool_iostat(self, zpool):
        """
        Retrieve vdev-specific stats using iostat -v.  Parses out all non-digits

        :param zpool:
        :return:
        """
        p = subprocess.Popen(
            'sudo zpool iostat -v {name}'.format(
                name=zpool
            ).split(),
            stdout=subprocess.PIPE
            )
        zpool_iostat_output, err = p.communicate()
        stats = {}
        vdev_count = 0
        vdev_name = "VDEV_"
        zpool_iostat_output = filter(None, zpool_iostat_output.split('\n'))[4:-1]

        # For each line from zpool iostat -v, find the vdevs and get their total and free space
        for line in zpool_iostat_output:
            properties = line.split()

            # We only care about parsing vdevs here for total and free space.  Lines from iostat
            # which are disk-only don't have total capacity, just '-', so we don't want to send
            # any information
            if properties[1][0] == '-':
                continue
            current_vdev = vdev_name + str(vdev_count)
            stats[current_vdev] = {}
            total = properties[1]
            free = properties[2]

            if re.match('^\d+[K,M,G,T]', free) or re.match('^\d+\.\d+[K,M,G,T]', free):
                free = self._convert_human_to_bytes(free)
            if re.match('^\d+[K,M,G,T]', total) or re.match('^\d+\.\d+[K,M,G,T]', total):
                total = self._convert_human_to_bytes(total)

            used = int(total) - int(free)
            percent_used = int((used / int(total)) * 100)
            if percent_used < 1:
                percent_used = 1
                
            stats[current_vdev]['total'] = total
            stats[current_vdev]['free'] = free
            stats[current_vdev]['percent_used'] = percent_used
            vdev_count += 1
        return stats

    def _get_zpool_checks(self, zpool):
        """
        Retrieve service check stats about zpool.  Returns as-is: no parsing

        :param zpool:
        :return:
        """
        p = self.subprocess.Popen(
            'sudo zpool get {props} {name}'.format(
                props=','.join(Zfs.zpool_service_checks),
                name=zpool
            ).split(),
            stdout=self.subprocess.PIPE
            )
        zpool_output, err = p.communicate()
        checks = {}
        for line in filter(None, zpool_output.split('\n')):
            properties = line.split()
            result = properties[2]
            # Stupid zpool command doesn't let you skip headers.  Toss this record
            if result == 'VALUE':
                continue
            checks[properties[1]] = result
        return checks

    @staticmethod
    def _convert_human_to_bytes(number):
        unit = number[-1:].upper()
        value = float(number[:-1])

        if unit == 'K':
            value *= 1024
        elif unit == 'M':
            value *= 1048576
        elif unit == 'G':
            value *= 1073741824
        elif unit == 'T':
            value *= 1099511627776
        elif unit not in ('K', 'M', 'G', 'T'):
            try:
                value = float(number)
            except ValueError:
                raise NotImplementedError
        return int(value)

    def _get_zfs_filesystems(self):
        """
        Get all zfs filesystems present on the host
        :return: List of zfs filesystems
        """
        p = self.subprocess.Popen(
            'sudo zfs list -o name -H'.split(),
            stdout=self.subprocess.PIPE
            )
        zfs_filesystems, err = p.communicate()
        return filter(None, zfs_filesystems.split('\n'))

    def _get_zfs_stats(self, zfs_name):
        p = self.subprocess.Popen(
            'sudo zfs get -o property,value -p {props} -H {name}'.format(
                props=','.join(Zfs.zfs_metrics),
                name=zfs_name).split(),
            stdout=self.subprocess.PIPE
            )
        zfs_output, err = p.communicate()
        stats = {}
        for line in filter(None, zfs_output.split('\n')):
            properties = line.split()
            stats[properties[0]] = re.sub("[^0-9,\.]", "", properties[1])
        return stats

    def _process_zfs_usage(self, zfs_name, zfs_stats):
        """
        Process zfs usage

        :param zfs_name: Name of zfs filesystem
        :param zfs_stats: Associated statistics
        :return: None
        """
        tags = [
            'zfs_name:{}'.format(zfs_name)
        ]

        try:
            total = int(zfs_stats[Zfs.ZFS_USED]) + int(zfs_stats[Zfs.ZFS_AVAILABLE])
            percent_used = int((int(zfs_stats[Zfs.ZFS_USED]) / total) * 100)
            if percent_used < 1:
                percent_used = 1
            self.gauge(Zfs.ZFS_NAMESPACE + 'total', str(total), tags=tags)
            self.gauge(Zfs.ZFS_NAMESPACE + 'percent_used', str(percent_used), tags=tags)

        except ValueError:
            self.log.debug("Could not determine total and percentage for zfs {name}, used {used}, avail {avail}".format(
                name=zfs_name,
                used=zfs_stats[Zfs.ZFS_USED],
                avail=zfs_stats[Zfs.ZFS_AVAILABLE]
            ))

        for metric in zfs_stats.keys():
            self.gauge(Zfs.ZFS_NAMESPACE + metric, zfs_stats[metric], tags=tags)

