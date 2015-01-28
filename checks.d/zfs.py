#!/usr/bin/python
from __future__ import division
from checks import AgentCheck
import subprocess

class Zfs(AgentCheck):

	ZFS_LIST_FORMAT = {
		'USED' : 0,
		'AVAIL': 1,
		'REFER' : 2,
		'MOUNTPOINT' : 3,
	}

	def check(self, instance):
		self.log.debug("Processing zfs data")
		self._process_zfs_usage()

	def _process_zfs_usage(self):
		# Read in zfs used and available
		# TODO: Figure out zfs permissioning so that sudo is not required

		# zfs get -o name,value -Hp used
		p = subprocess.Popen(
				"sudo zfs get -o name,value -Hp used".split(), 
				stdout=subprocess.PIPE
			)
		zfs_used_output, err = p.communicate()

		# zfs get -o name,value -Hp available
		p = subprocess.Popen(
				"sudo zfs get -o name,value -Hp available".split(), 
				stdout=subprocess.PIPE
			)
		zfs_available_output, err = p.communicate()

		# Parse the output
		zfs_used = {}
		for line in zfs_used_output.split('\n'):
			temp_list = line.split()
			if temp_list:
				self.log.info(temp_list)
				zfs_used[temp_list[0]] = temp_list[1]
		
		zfs_available = {}
		for line in zfs_available_output.split('\n'):
			temp_list = line.split()
			if temp_list:
				self.log.info(temp_list)	
				zfs_available[temp_list[0]] = temp_list[1]

		for name in zfs_used.keys():
			try:
				used = int(zfs_used[name])
				available = int(zfs_available[name])
			except(ValueError):
				continue
			
			total = used + available
			percent_used = (used / total) * 100
			if percent_used < 1:
				percent_used = 1

			tags = [
                "name:%s" % (name, )
            ]

			self.gauge('system.zfs.used', used, tags=tags)
			self.gauge('system.zfs.available', available, tags=tags)
			self.gauge('system.zfs.total', total, tags=tags)
			self.gauge('system.zfs.percent_used', percent_used, tags=tags)

	def _parse_zpool_status(self):
		# Get list of zpools
		p = subprocess.Popen(
				"sudo zpool list -H".split(), 
				stdout=subprocess.PIPE
			)
		zfs_pools_output, err = p.communicate()
		zpools = []
		for line in zfs_pools_output.split('\n'):
			zpools.append(line.split()[0])

		# For each zpool, get the health
		for zpool in zpools:
			p = subprocess.Popen(
					"sudo zpool get health {}".format(zpool).split(), 
					stdout=subprocess.PIPE
				)
			health_output, err = p.communicate()
			health_line = health_output.split('\n')[1]
			health_status = health_line.split()[2]
			check_status = None
			if health_status == 'ONLINE':
				check_status = AgentCheck.OK
			elif check_status == 'DEGRADED':
				check_status = AgentCheck.WARNING
			else:
				check_status = AgentCheck.CRITICAL

			self.service_check('system.zfs.zpoolhealth', check_status)








