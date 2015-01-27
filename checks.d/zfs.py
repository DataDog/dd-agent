#!/usr/bin/python
from __future__ import division
from checks import AgentCheck

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
		# zfs get -o name,value -Hp used
		# zfs get -o name,value -Hp available
		# TODO: Read from command line

		# Temp hack to read from files
		zfs_used_file = open('./zfs_get_used.out', 'r')
		zfs_used_output = zfs_used_file.read()
		zfs_used_file.close()
		
		zfs_available_file = open('./zfs_get_available.out')
		zfs_available_output = zfs_available_file.read()
		zfs_available_file.close()

		# Parse the output
		zfs_used = {}
		for line in zfs_used_output.split('\n'):
			temp_list = line.split()
			zfs_used[temp_list[0]] = temp_list[1]
		
		zfs_available = {}
		for line in zfs_available_output.split('\n'):
			temp_list = line.split()
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

		
	def _parse_zpool_list(self):
		# Read in zpool list output
		# TODO: Read from command line

		# Temp hack to read from file
		pass
	def _parse_zpool_status(self):
		# Read in zpool status output
		# TODO: Read from command line

		# Temp hack to read from file
		pass

print("Hello")
zc = ZfsCheck()
zc.parse_zfs_usage()