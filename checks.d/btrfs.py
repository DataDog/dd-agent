#####
# This is adapted from btrfs-gui: http://carfax.org.uk/btrfs-gui (License included)
# It mimics the behavior of the btrfs fi df command
#

# stdlib
import os
import struct
import array
import itertools
import fcntl

# project
from checks import AgentCheck

# 3rd party
import psutil

BLOCK_GROUP_DATA = 1 << 0
BLOCK_GROUP_SYSTEM = 1 << 1
BLOCK_GROUP_METADATA = 1 << 2
BLOCK_GROUP_RAID0 = 1 << 3
BLOCK_GROUP_RAID1 = 1 << 4
BLOCK_GROUP_DUP = 1 << 5
BLOCK_GROUP_RAID10 = 1 << 6 

IOCTL_SPACE_ARGS = struct.Struct("=2Q")
IOC_SPACE_INFO = 0xc0109414
IOCTL_SPACE_INFO = struct.Struct("=3Q")

def sized_array(count=4096):
    return array.array("B", itertools.repeat(0, count))

def get_replication_type(bgid):
    if bgid & BLOCK_GROUP_RAID0:
        return "RAID0"
    elif bgid & BLOCK_GROUP_RAID1:
        return "RAID1"
    elif bgid & BLOCK_GROUP_RAID10:
        return "RAID10"
    elif bgid & BLOCK_GROUP_DUP:
        return "DUP"
    return "single"

def get_usage_type(bgid):
    if (bgid & BLOCK_GROUP_DATA) and (bgid & BLOCK_GROUP_METADATA):
        return "mixed"
    elif bgid & BLOCK_GROUP_DATA:
        return "data"
    elif bgid & BLOCK_GROUP_METADATA:
        return "metadata"
    elif bgid & BLOCK_GROUP_SYSTEM:
        return "system"
    return ""

class Filesystem(object):

    class _DirFD(object):
        def __init__(self, fd):
            self.fd = fd

        def fileno(self):
            return self.fd

        def open(self, dir):
            return self.fd

    def __init__(self, mountpoint):
        self.mountpoint = mountpoint

    def __enter__(self):
        self.fd = os.open(self.mountpoint, os.O_DIRECTORY)
        return self._DirFD(self.fd)

    def __exit__(self, exc_type, exc_value, traceback):
        os.close(self.fd)

def df(mountpoint):
    """Collect information on the usage of the filesystem. Replicate
    the operation of btrfs fi df.
    """

    with Filesystem(mountpoint) as fd:
        # Get the number of spaces we need to allocate for the result
        ret = sized_array(IOCTL_SPACE_ARGS.size)
        rv = fcntl.ioctl(fd, IOC_SPACE_INFO, ret)
        space_slots, total_spaces = IOCTL_SPACE_ARGS.unpack(ret)

        # Now allocate it, and get the data
        buf_size = (IOCTL_SPACE_ARGS.size
                    + total_spaces * IOCTL_SPACE_INFO.size)
        ret = sized_array(buf_size)
        IOCTL_SPACE_ARGS.pack_into(ret, 0, total_spaces, 0)
        rv = fcntl.ioctl(fd, IOC_SPACE_INFO, ret)

    # Parse the result
    space_slots, total_spaces = IOCTL_SPACE_ARGS.unpack_from(ret, 0)

    res = []
    for offset in xrange(IOCTL_SPACE_ARGS.size,
                         buf_size,
                         IOCTL_SPACE_INFO.size):
        flags, total, used = IOCTL_SPACE_INFO.unpack_from(ret, offset)
        res.append({"flags": flags, "size": total, "used": used})

    return res

class BTRFS(AgentCheck):

    def __init__(self, name, init_config, agentConfig, instances=None):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances=instances)
        if instances is not None and len(instances) > 1:
            raise Exception("BTRFS check only supports one configured instance.")

    def check(self, instance):
        btrfs_devices = {}
        excluded_devices = instance.get('excluded_devices', [])
        for p in psutil.disk_partitions():
            if p.fstype == 'btrfs' and p.device not in btrfs_devices\
             and p.device not in excluded_devices:
                btrfs_devices[p.device] = p.mountpoint

        if len(btrfs_devices) == 0:
            raise Exception("No btrfs device found")

        for device, mountpoint in btrfs_devices.iteritems():
            v = df(mountpoint)
            for data in v:
                tags = [
                    'usage_type:' + get_usage_type(data['flags']),
                    'replication_type:' + get_replication_type(data['flags']),
                ]
                total = data['size']
                used = data['used']
                free = total - used
                usage = free / total

                self.gauge('system.disk.btrfs.total', total, tags=tags, device_name=device)
                self.gauge('system.disk.btrfs.used', used, tags=tags, device_name=device)
                self.gauge('system.disk.btrfs.free', free, tags=tags, device_name=device)
                self.gauge('system.disk.btrfs.usage', usage, tags=tags, device_name=device)
