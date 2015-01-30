#!/usr/bin/python
from __future__ import division
from checks import AgentCheck
import subprocess
import re

'''
Matt, you need to update the whole thing to use the metrics[] and service_checks[] paradigm that you've
begun to implement in _process_zpools.  That'll simplify the calls.
'''
class Zfs(AgentCheck):

    ZFS_NAMESPACE = 'system.zfs.'
    ZFS_AVAILABLE = 'available'
    ZFS_USED = 'used'
    ZFS_COMPRESSRATIO = 'compressratio'

    ZPOOL_NAMESPACE = 'zpool.'
    ZPOOL_CAPACITY = 'capacity'
    ZPOOL_SIZE = 'size'
    ZPOOL_DEDUPRATIO = 'dedupratio'
    ZPOOL_FREE = 'free'
    ZPOOL_ALLOCATED = 'allocated'
    ZPOOL_HEALTH = 'health'

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
            

    def _process_zpools(self, zpools):
        pass
        # metrics_report = {}
        # service_check_report = {}
        #
        # # For each zpool, report on the pertinent metrics
        # for zpool in zpools:
        #     p = subprocess.Popen(
        #         'sudo zpool get all {}'.format(zpool).split(),
        #         stdout=subprocess.PIPE
        #         )
        #     zpool_get_output, err = p.communicate()
        #     zpool_get_lines = zpool_get_output.split('\n')[1:]
        #
        #     for line in zpool_get_lines:
        #         line_breakdown = line.split()
        #         check_name = line_breakdown[1]
        #         check_value = line_breakdown[2]
        #         if check_name in metrics:
        #             metrics_report[check_name] = check_value
        #         elif check_name in service_checks:
        #             service_check_report[check_name] = check_value

            # tags = [
            #     'name:%s' % (zpool, )
            # ]
            #
            # check_status = None
            # if health_status == 'ONLINE':
            #     check_status = AgentCheck.OK
            # elif check_status == 'DEGRADED':
            #     check_status = AgentCheck.WARNING
            # else:
            #     check_status = AgentCheck.CRITICAL
            #
            # self.service_check('system.zfs.zpoolhealth', check_status, tags=tags, message=health_status)

    @staticmethod
    def _get_zpools():
        """
        Get list of zpools
        :return: List of zpools
        """
        p = subprocess.Popen(
            'sudo zpool list -H -o name'.split(),
            stdout=subprocess.PIPE
            )
        zpools, err = p.communicate()
        return filter(None, zpools.split('\n'))

    def _get_zpool_stats(self, zpool):
        """
        Retrieve numerical statistics about zpool.  Parses out all non-digits

        :param zpool:
        :return:
        """
        p = subprocess.Popen(
            'sudo zpool get {props} {name}'.format(
                props=','.join(Zfs.zpool_metrics + Zfs.zpool_service_checks),
                name=zpool
            ).split(),
            stdout=subprocess.PIPE
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
            stats[properties[1]] = re.sub("[^0-9,\.]", "", result)
        return stats

    def _get_zpool_checks(self, zpool):
        """
        Retrieve service check stats about zpool.  Returns as-is: no parsing

        :param zpool:
        :return:
        """
        p = subprocess.Popen(
            'sudo zpool get {props} {name}'.format(
                props=','.join(Zfs.zpool_service_checks),
                name=zpool
            ).split(),
            stdout=subprocess.PIPE
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
        value = int(number[:-1])
        if unit == 'K':
            value *= 1024
        elif unit == 'M':
            value *= 1048576
        elif unit == 'G':
            value *= 1073741824
        elif unit == 'T':
            value *= 1099511627776
        return int(value)

    @staticmethod
    def _get_zfs_filesystems():
        """
        Get all zfs filesystems present on the host
        :return: List of zfs filesystems
        """
        p = subprocess.Popen(
            'sudo zfs list -o name -H'.split(),
            stdout=subprocess.PIPE
            )
        zfs_filesystems, err = p.communicate()
        return filter(None, zfs_filesystems.split('\n'))


    @staticmethod
    def _get_zfs_stats(zfs_name):
        p = subprocess.Popen(
            'sudo zfs get -o property,value -p {props} -H {name}'.format(
                props=','.join(Zfs.zfs_metrics),
                name=zfs_name).split(),
            stdout=subprocess.PIPE
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
            percent_used = (int(zfs_stats[Zfs.ZFS_USED]) / total) * 100
            if percent_used < 1:
                percent_used = 1
            self.gauge(Zfs.ZFS_NAMESPACE + 'total', total, tags=tags)
            self.gauge(Zfs.ZFS_NAMESPACE + 'percent_used', percent_used, tags=tags)

        except ValueError:
            self.log.debug("Could not determine total and percentage for zfs {name}, used {used}, avail {avail}".format(
                name=zfs_name,
                used=zfs_stats[Zfs.ZFS_USED],
                avail=zfs_stats[Zfs.ZFS_AVAILABLE]
            ))

        for metric in zfs_stats.keys():
            self.gauge(Zfs.ZFS_NAMESPACE + metric, zfs_stats[metric], tags=tags)

    def get_library_versions(self):
        return NotImplemented