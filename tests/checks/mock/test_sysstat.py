# stdlib
import logging
import sys
import unittest
import mock

# project
from checks.system.unix import (
    IO,
    Load,
    Memory,
)
from checks.system.unix import System
from config import get_system_stats
from utils.platform import Platform

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__file__)


class TestSystem(unittest.TestCase):

    def testUptime(self):
        global logger
        system = System(logger)
        metrics = system.check({})
        self.assertTrue("system.uptime" in metrics)
        self.assertTrue(metrics["system.uptime"] > 0)

    def testLoad(self):
        global logger
        load = Load(logger)
        res = load.check({'system_stats': get_system_stats()})
        assert 'system.load.1' in res
        if Platform.is_linux():
            cores = int(get_system_stats().get('cpuCores'))
            assert 'system.load.norm.1' in res
            assert abs(res['system.load.1'] - cores * res['system.load.norm.1']) <= 0.1, (res['system.load.1'], cores * res['system.load.norm.1'])

        # same test but without cpu count, no normalized load sent.
        res = load.check({})
        assert 'system.load.1' in res
        assert 'system.load.norm.1' not in res

    def testMemory(self):
        global logger
        res = Memory(logger).check({})
        if Platform.is_linux():
            MEM_METRICS = ["swapTotal", "swapFree", "swapPctFree", "swapUsed", "physTotal", "physFree", "physUsed", "physBuffers", "physCached", "physUsable", "physPctUsable", "physShared"]
            for k in MEM_METRICS:
                # % metric is only here if total > 0
                if k == 'swapPctFree' and res['swapTotal'] == 0:
                    continue
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
sda               0.00     0.00    0.00    0.00     0.00     0.00     0.00     0.00    0.00    0.00    0.00   0.00   0.01

"""

        global logger
        checker = IO(logger)
        results = checker._parse_linux2(debian_iostat_output)
        self.assertTrue('sda' in results)
        for key in ('rrqm/s', 'wrqm/s', 'r/s', 'w/s', 'rkB/s', 'wkB/s',
                    'avgrq-sz', 'avgqu-sz', 'await', 'r_await',
                    'w_await', 'svctm', '%util'):
            self.assertTrue(key in results['sda'], 'key %r not in results["sda"]' % key)
            if key == r'%util':
                expected = 0.01
            else:
                expected = '0.00'
            self.assertEqual(results['sda'][key], expected)

        # example output from `iostat -d 1 2 -x -k` on
        # ubuntu 18.04 x86_64, from deb package
        # sysstat@11.6.1-1; main breaking change is
        # that header starts with `Device` instead of `Device:`.
        newer_iostat_output = """Linux 4.9.60-linuxkit-aufs (f3cf72f6fb4d)     05/09/18    _x86_64_    (2 CPU)

Device            r/s     w/s     rkB/s     wkB/s   rrqm/s   wrqm/s  %rrqm  %wrqm r_await w_await aqu-sz rareq-sz wareq-sz  svctm  %util
sda              0.07    0.08      0.64      5.44     0.00     0.23   0.41  72.99    2.42   19.91   0.00     8.92    65.13   0.38   0.01

Device            r/s     w/s     rkB/s     wkB/s   rrqm/s   wrqm/s  %rrqm  %wrqm r_await w_await aqu-sz rareq-sz wareq-sz  svctm  %util
sda              0.00    0.00      0.00      0.00     0.00     0.00   0.00   0.00    0.00    0.00   0.00     0.00     0.00   0.00   0.01

"""

        checker = IO(logger)
        results = checker._parse_linux2(newer_iostat_output)
        self.assertTrue('sda' in results)
        for key in ('rrqm/s', 'wrqm/s', 'r/s', 'w/s', 'rkB/s', 'wkB/s',
                    'r_await', 'w_await', 'svctm', '%util'):
            self.assertTrue(key in results['sda'], 'key %r not in results["sda"]' % key)
            if key == r'%util':
                expected = 0.01
            else:
                expected = '0.00'
            self.assertEqual(results['sda'][key], expected)

        # example output from `iostat -d 1 d -x -k` on
        # centos 5.8 x86_64, from RPM package
        # sysstat@7.0.2; it differs from the first one by
        # not having split-out r_await and w_await fields
        centos_iostat_output = """Linux 2.6.18-308.el5 (localhost.localdomain)  05/29/2012

Device:         rrqm/s   wrqm/s   r/s   w/s    rkB/s    wkB/s avgrq-sz avgqu-sz   await  svctm  %util
sda               9.44     7.56 16.76  4.40   322.05    47.75    34.96     0.01    0.59   0.35   0.74

Device:         rrqm/s   wrqm/s   r/s   w/s    rkB/s    wkB/s avgrq-sz avgqu-sz   await  svctm  %util
sda               0.00     0.00  0.00  0.00     0.00     0.00     0.00     0.00    0.00   0.00   0.01

"""

        checker = IO(logger)
        results = checker._parse_linux2(centos_iostat_output)
        self.assertTrue('sda' in results)
        for key in ('rrqm/s', 'wrqm/s', 'r/s', 'w/s', 'rkB/s', 'wkB/s',
                    'avgrq-sz', 'avgqu-sz', 'await', 'svctm', '%util'):
            self.assertTrue(key in results['sda'], 'key %r not in results["sda"]' % key)
            if key == r'%util':
                expected = 0.01
            else:
                expected = '0.00'
            self.assertEqual(results['sda'][key], expected)

        # iostat -o -d -c 2 -w 1
        # OS X 10.8.3 (internal SSD + USB flash attached)
        darwin_iostat_output = """          disk0           disk1
    KB/t tps  MB/s     KB/t tps  MB/s
   21.11  23  0.47    20.01   0  0.00
    6.67   3  0.02     0.00   0  0.00
"""
        checker = IO(logger)
        results = checker._parse_darwin(darwin_iostat_output)
        self.assertTrue("disk0" in results.keys())
        self.assertTrue("disk1" in results.keys())

        self.assertEqual(
            results["disk0"],
            {'system.io.bytes_per_s': float(0.02 * 2**20),}
        )
        self.assertEqual(
            results["disk1"],
            {'system.io.bytes_per_s': float(0),}
        )


        linux_output_dashes = """Linux 3.13.0-32-generic (ubuntu-1204)  05/20/2016  _x86_64_    (2 CPU)

Device:         rrqm/s   wrqm/s     r/s     w/s    rkB/s    wkB/s avgrq-sz avgqu-sz   await r_await w_await  svctm  %util
sda               5.77     8.20    7.79   30.08   320.67   219.91    28.55     0.05    1.32    1.53    1.27   0.32   1.20
dm-0              0.00     0.00   11.71   37.97   313.61   219.90    21.48     0.11    2.16    2.13    2.17   0.24   1.20
dm-1              0.00     0.00    0.08    0.00     0.32     0.00     8.00     0.00    1.68    1.68    0.00   1.07   0.01

Device:         rrqm/s   wrqm/s     r/s     w/s    rkB/s    wkB/s avgrq-sz avgqu-sz   await r_await w_await  svctm  %util
sda               0.00     0.00    0.00    1.00     0.00     4.00     8.00     0.00    0.00    0.00    0.00   0.00   0.00
dm-0              0.00     0.00    0.00    1.00     0.00     4.00     8.00     0.00    0.00    0.00    0.00   0.00   0.00
dm-1              0.00     0.00    0.00    0.00     0.00     0.00     0.00     0.00    0.00    0.00    0.00   0.00   0.00
"""
        results = checker._parse_linux2(linux_output_dashes)
        self.assertTrue(sorted(results.keys()) == ['dm-0', 'dm-1', 'sda'])

    def testLinuxCapIostat(self):
        # example output from `iostat -d 1 2 -x -k` on
        # debian testing x86_64, from Debian package
        # sysstat@10.0.4-1
        debian_iostat_output = """Linux 3.2.0-2-amd64 (fireflyvm)   05/29/2012  _x86_64_    (2 CPU)

Device:         rrqm/s   wrqm/s     r/s     w/s    rkB/s    wkB/s avgrq-sz avgqu-sz   await r_await w_await  svctm  %util
sda               0.44     2.58    5.79    2.84   105.53   639.03   172.57     0.17   19.38    1.82   55.26   0.66   0.57

Device:         rrqm/s   wrqm/s     r/s     w/s    rkB/s    wkB/s avgrq-sz avgqu-sz   await r_await w_await  svctm  %util
sda               0.00     0.00    0.00    0.00     0.00     0.00     0.00     0.00    0.00    0.00    0.00   0.00   100.01

"""

        global logger
        checker = IO(logger)
        results = checker._parse_linux2(debian_iostat_output)
        self.assertTrue('sda' in results)
        # Ensure that value is capped and return to 0 if it surpasses 100
        expected = 0
        self.assertEqual(results['sda']['%util'], expected)

        # example output from `iostat -d 1 2 -x -k` on
        # ubuntu 18.04 x86_64, from deb package
        # sysstat@11.6.1-1; main breaking change is
        # that header starts with `Device` instead of `Device:`.
        newer_iostat_output = """Linux 4.9.60-linuxkit-aufs (f3cf72f6fb4d)     05/09/18    _x86_64_    (2 CPU)

Device            r/s     w/s     rkB/s     wkB/s   rrqm/s   wrqm/s  %rrqm  %wrqm r_await w_await aqu-sz rareq-sz wareq-sz  svctm  %util
sda              0.07    0.08      0.64      5.44     0.00     0.23   0.41  72.99    2.42   19.91   0.00     8.92    65.13   0.38   0.01

Device            r/s     w/s     rkB/s     wkB/s   rrqm/s   wrqm/s  %rrqm  %wrqm r_await w_await aqu-sz rareq-sz wareq-sz  svctm  %util
sda              0.00    0.00      0.00      0.00     0.00     0.00   0.00   0.00    0.00    0.00   0.00     0.00     0.00   0.00   99.99

"""

        checker = IO(logger)
        results = checker._parse_linux2(newer_iostat_output)
        self.assertTrue('sda' in results)
        expected = 99.99
        self.assertEqual(results['sda']['%util'], expected)

        # example output from `iostat -d 1 d -x -k` on
        # centos 5.8 x86_64, from RPM package
        # sysstat@7.0.2; it differs from the first one by
        # not having split-out r_await and w_await fields
        centos_iostat_output = """Linux 2.6.18-308.el5 (localhost.localdomain)  05/29/2012

Device:         rrqm/s   wrqm/s   r/s   w/s    rkB/s    wkB/s avgrq-sz avgqu-sz   await  svctm  %util
sda               9.44     7.56 16.76  4.40   322.05    47.75    34.96     0.01    0.59   0.35   0.74

Device:         rrqm/s   wrqm/s   r/s   w/s    rkB/s    wkB/s avgrq-sz avgqu-sz   await  svctm  %util
sda               0.00     0.00  0.00  0.00     0.00     0.00     0.00     0.00    0.00   0.00   102.01

"""

        checker = IO(logger)
        results = checker._parse_linux2(centos_iostat_output)
        self.assertTrue('sda' in results)
        # %util value is over 100, and value is set to 0
        expected = 0
        self.assertEqual(results['sda']['%util'], expected)

    def sunos5_output(self, *args, **kwargs):
        output = """extended device statistics <-- since boot
device      r/s    w/s   kr/s   kw/s wait actv  svc_t  %w  %b
ramdisk1    0.0    0.0    0.1    0.1  0.0  0.0    0.0   0   0
sd0         0.0    0.0    0.0    0.0  0.0  0.0    0.0   0   0
sd1        79.9  149.9 1237.6 6737.9  0.0  0.5    2.3   0  11
                   extended device statistics <-- past second
device      r/s    w/s   kr/s   kw/s wait actv  svc_t  %w  %b
ramdisk1    0.0    0.0    0.0    0.0  0.0  0.0    0.0   0   0
sd0         0.0    0.0    0.0    0.0  0.0  0.0    0.0   0   102
sd1         0.0  139.0    0.0 1850.6  0.0  0.0    0.1   0   10
"""     
        return output, 0, 0

    def freebsd_output(self, *args, **kwargs):
        output = """extended device statistics
device     r/s   w/s    kr/s    kw/s wait svc_t  %b
ad0        3.1   1.3    49.9    18.8    0   0.7   0
extended device statistics
device     r/s   w/s    kr/s    kw/s wait svc_t  %b
ad0        0.0   2.0     0.0    31.8    0   0.2   102
"""     
        return output, 0, 0

    @mock.patch('checks.system.unix.sys.platform', 'sunos5')
    @mock.patch('checks.system.unix.get_subprocess_output', side_effect=sunos5_output)
    def testSunos5CapIostat(self, mock_subprocess):
        global logger
        checker = IO(logger)
        results = checker.check({})
        for res in results:
            if res == 'sd1':
                expected = 10
            else:
                expected = 0
            self.assertEqual(results[res]['%util'], expected)

    @mock.patch('checks.system.unix.sys.platform', 'freebsd')
    @mock.patch('checks.system.unix.get_subprocess_output', side_effect=freebsd_output)
    def testFreebsdCapIostat(self, mock_subprocess):
        global logger
        checker = IO(logger)
        results = checker.check({})
        expected = 0
        for res in results:
            self.assertEqual(results[res]['%util'], expected)
