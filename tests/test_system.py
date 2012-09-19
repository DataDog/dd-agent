import unittest
import logging
import sys

logger = logging.getLogger(__file__)

from checks.system.unix import *

class TestSystem(unittest.TestCase):
    def testCPU(self):
        global logger
        cpu = Cpu()
        res = cpu.check(logger, {})
        # Make sure we sum up to 100% (or 99% in the case of macs)
        assert abs(reduce(lambda a,b:a+b, res.values(), 0) - 100) <= 1, res

    def testDisk(self):
        """Testing disk stats gathering"""
        global logger
        disk = Disk(logger)
        res = disk.check({})

    lion_df_i = """Filesystem                        512-blocks      Used Available Capacity  iused    ifree %iused  Mounted onto
/dev/disk1                         487932936 220080040 267340896    46% 27574003 33417612   45%   /
devfs                                    374       374         0   100%      648        0  100%   /dev
map -hosts                                 0         0         0   100%        0        0  100%   /net
map auto_home                              0         0         0   100%        0        0  100%   /home
localhost:/KJDS7Bgpbp1QglL9lBwOe6  487932936 487932936         0   100%        0        0  100%   /Volumes/MobileBackups
/dev/disk2s1                        62309376   5013120  57296256     9%        0        0  100%   /Volumes/NO name"""
        
    lion_df_k = """Filesystem                        1024-blocks      Used Available Capacity  Mounted onto
/dev/disk1                          243966468 110040020 133670448    46%    /
devfs                                     187       187         0   100%    /dev
map -hosts                                  0         0         0   100%    /net
map auto_home                               0         0         0   100%    /home
localhost:/KJDS7Bgpbp1QglL9lBwOe6   243966468 243966468         0   100%    /Volumes/MobileBackups
/dev/disk2s1                         31154688   2506560  28648128     9%    /Volumes/NO NAME"""

    linux_df_k = """Filesystem           1K-blocks      Used Available Use% Mounted on
/dev/sda1              8256952   5600592   2236932  72% /
none                   3802316       124   3802192   1% /dev
none                   3943856         0   3943856   0% /dev/shm
none                   3943856       148   3943708   1% /var/run
none                   3943856         0   3943856   0% /var/lock
none                   3943856         0   3943856   0% /lib/init/rw
/dev/sdb             433455904    305360 411132240   1% /mnt
/dev/sdf              52403200  40909112  11494088  79% /data
nfs:/abc/def/ghi/jkl/mno/pqr
                      52403200  40909112  11494088  79% /data2
/dev/sdg              52403200  40909112  11494088  79% /data3
"""

    linux_df_i = """Filesystem            Inodes   IUsed   IFree IUse% Mounted on
/dev/sda1             524288  171642  352646   33% /
none                  950579    2019  948560    1% /dev
none                  985964       1  985963    1% /dev/shm
none                  985964      66  985898    1% /var/run
none                  985964       3  985961    1% /var/lock
none                  985964       1  985963    1% /lib/init/rw
/dev/sdb             27525120     147 27524973    1% /mnt
/dev/sdf             46474080  478386 45995694    2% /data
"""

    def testDfParser(self):
        global logger
        disk = Disk(logger)

        if sys.platform == 'darwin':
            res = disk._parse_df(TestSystem.lion_df_k)
            assert res[0][:4] == ["/dev/disk1", 243966468, 110040020, 133670448], res[0]
            assert res[3][:4] == ["/dev/disk2s1", 31154688, 2506560, 28648128], res[3]

            res = disk._parse_df(TestSystem.lion_df_i, inodes = True)
            assert res[0][:4] == ["/dev/disk1", 60991615, 27574003, 33417612], res[0]

        if sys.platform == 'linux2':
            res = disk._parse_df(TestSystem.linux_df_k)
            assert res[0][:4] == ["/dev/sda1", 8256952, 5600592,  2236932], res[0]
            assert res[-3][:4] == ["/dev/sdf", 52403200, 40909112, 11494088], res[-2]
            assert res[-2][:4] == ["nfs:/abc/def/ghi/jkl/mno/pqr", 52403200, 40909112, 11494088], res[-1]
            assert res[-1][:4] == ["/dev/sdg", 52403200, 40909112, 11494088], res[-2]
    
            res = disk._parse_df(TestSystem.linux_df_i, inodes = True)
            assert res[0][:4] == ["/dev/sda1", 524288, 171642, 352646], res[0]
            assert res[1][:4] == ["/dev/sdb", 27525120, 147, 27524973], res[1]
            assert res[2][:4] == ["/dev/sdf", 46474080, 478386, 45995694], res[2]
    
            res = disk._parse_df(TestSystem.linux_df_k, use_mount = True)
            assert res[0][:4] == ["/", 8256952, 5600592,  2236932], res[0]
            assert res[-3][:4] == ["/data", 52403200, 40909112, 11494088], res[-2]
            assert res[-2][:4] == ["/data2", 52403200, 40909112, 11494088], res[-1]
            assert res[-1][:4] == ["/data3", 52403200, 40909112, 11494088], res[-2]
        

    def testMemory(self):
        global logger
        res = Memory(logger).check({})
        if sys.platform == 'linux2':
            for k in ("swapTotal", "swapFree", "swapUsed", "physTotal", "physFree", "physUsed", "physBuffers", "physCached", "physUsable", "physShared"):
                assert k in res, res
            assert res["swapTotal"] == res["swapFree"] + res["swapUsed"]
            assert res["physTotal"] == res["physFree"] + res["physUsed"]
        elif sys.platform == 'darwin':
            for k in ("swapFree", "swapUsed", "physFree", "physUsed"):
                assert k in res, res

    def testDiskLatency(self):
        # example output from `iostat -d 1 2 -x -k` on
        # debian testing x86_64, from Debian package
        # sysstat@10.0.4-1
        debian_iostat_output = """Linux 3.2.0-2-amd64 (fireflyvm)   05/29/2012  _x86_64_    (2 CPU)

Device:         rrqm/s   wrqm/s     r/s     w/s    rkB/s    wkB/s avgrq-sz avgqu-sz   await r_await w_await  svctm  %util
sda               0.44     2.58    5.79    2.84   105.53   639.03   172.57     0.17   19.38    1.82   55.26   0.66   0.57

Device:         rrqm/s   wrqm/s     r/s     w/s    rkB/s    wkB/s avgrq-sz avgqu-sz   await r_await w_await  svctm  %util
sda               0.00     0.00    0.00    0.00     0.00     0.00     0.00     0.00    0.00    0.00    0.00   0.00   0.00

"""

        checker = IO()
        results = checker._parse_linux2_iostat_output(debian_iostat_output)
        self.assertTrue('sda' in results)
        for key in ('rrqm/s', 'wrqm/s', 'r/s', 'w/s', 'rkB/s', 'wkB/s',
                    'avgrq-sz', 'avgqu-sz', 'await', 'r_await',
                    'w_await', 'svctm', '%util'):
            self.assertTrue(key in results['sda'], 'key %r not in results["sda"]' % key)
            self.assertEqual(results['sda'][key], '0.00')

        # example output from `iostat -d 1 d -x -k` on
        # centos 5.8 x86_64, from RPM package
        # sysstat@7.0.2; it differs from the above by
        # not having split-out r_await and w_await fields
        centos_iostat_output = """Linux 2.6.18-308.el5 (localhost.localdomain)  05/29/2012

Device:         rrqm/s   wrqm/s   r/s   w/s    rkB/s    wkB/s avgrq-sz avgqu-sz   await  svctm  %util
sda               9.44     7.56 16.76  4.40   322.05    47.75    34.96     0.01    0.59   0.35   0.74

Device:         rrqm/s   wrqm/s   r/s   w/s    rkB/s    wkB/s avgrq-sz avgqu-sz   await  svctm  %util
sda               0.00     0.00  0.00  0.00     0.00     0.00     0.00     0.00    0.00   0.00   0.00

"""

        checker = IO()
        results = checker._parse_linux2_iostat_output(centos_iostat_output)
        self.assertTrue('sda' in results)
        for key in ('rrqm/s', 'wrqm/s', 'r/s', 'w/s', 'rkB/s', 'wkB/s',
                    'avgrq-sz', 'avgqu-sz', 'await', 'svctm', '%util'):
            self.assertTrue(key in results['sda'], 'key %r not in results["sda"]' % key)
            self.assertEqual(results['sda'][key], '0.00')

    def testNetwork(self):
        global logger
        checker = Network(logger)
        # First call yields nothing
        self.assertEquals(False, checker.check({}))
        # Second call yields values
        if sys.platform == "darwin":
            v = checker.check({})
            assert "lo0" in v
            

if __name__ == "__main__":
    unittest.main()