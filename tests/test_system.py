import unittest
import logging

logging.basicConfig()
logger = logging.getLogger()

from checks.system import *

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
        disk = Disk()
        res = disk.check(logger, {})

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
                      52403200  40909112  11494088  79% /data
/dev/sdg              52403200  40909112  11494088  79% /data
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
        disk = Disk()

        import sys
        sys.platform = 'darwin'
        res = disk._parse_df(TestSystem.lion_df_k)
        assert res[0][:4] == ["/dev/disk1", 243966468 / 1024 / 1024, 110040020 / 1024 / 1024, 133670448 / 1024 / 1024], res[0]
        assert res[3][:4] == ["/dev/disk2s1", 31154688 / 1024 / 1024, 2506560 / 1024 / 1024, 28648128 / 1024 / 1024], res[3]

        res = disk._parse_df(TestSystem.lion_df_i, inodes = True)
        assert res[0][:4] == ["/dev/disk1", 60991615, 27574003, 33417612], res[0]

        sys.platform = 'linux2'
        res = disk._parse_df(TestSystem.linux_df_k)
        assert res[0][:4] == ["/dev/sda1", 8256952 / 1024 / 1024, 5600592 / 1024 / 1024,  2236932 / 1024 / 1024], res[0]
        assert res[-3][:4] == ["/dev/sdf", 52403200 / 1024 / 1024, 40909112 / 1024 / 1024, 11494088 / 1024 / 1024], res[-2]
        assert res[-2][:4] == ["nfs:/abc/def/ghi/jkl/mno/pqr", 52403200 / 1024 / 1024, 40909112 / 1024 / 1024, 11494088 / 1024 / 1024], res[-1]
        assert res[-1][:4] == ["/dev/sdg", 52403200 / 1024 / 1024, 40909112 / 1024 / 1024, 11494088 / 1024 / 1024], res[-2]

        res = disk._parse_df(TestSystem.linux_df_i, inodes = True)
        assert res[0][:4] == ["/dev/sda1", 524288, 171642, 352646], res[0]
        assert res[1][:4] == ["/dev/sdb", 27525120, 147, 27524973], res[1]
        assert res[2][:4] == ["/dev/sdf", 46474080, 478386, 45995694], res[2]

if __name__ == "__main__":
    unittest.main()
