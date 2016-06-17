# stdlib
import logging
import sys
import unittest

# project
from checks.system.unix import (
    IO,
    Load,
    Memory,
)
from checks.system.unix import System
from config import get_system_stats
from tests.checks.common import get_check
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
sda               0.00     0.00    0.00    0.00     0.00     0.00     0.00     0.00    0.00    0.00    0.00   0.00   0.00

"""

        global logger
        checker = IO(logger)
        results = checker._parse_linux2(debian_iostat_output)
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

        checker = IO(logger)
        results = checker._parse_linux2(centos_iostat_output)
        self.assertTrue('sda' in results)
        for key in ('rrqm/s', 'wrqm/s', 'r/s', 'w/s', 'rkB/s', 'wkB/s',
                    'avgrq-sz', 'avgqu-sz', 'await', 'svctm', '%util'):
            self.assertTrue(key in results['sda'], 'key %r not in results["sda"]' % key)
            self.assertEqual(results['sda'][key], '0.00')

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

    def testNetwork(self):
        # FIXME: cx_state to true, but needs sysstat installed
        config = """
init_config:

instances:
    - collect_connection_state: false
      excluded_interfaces:
        - lo
        - lo0
"""
        check, instances = get_check('network', config)

        check.check(instances[0])
        check.get_metrics()

        metric_names = [m[0] for m in check.aggregator.metrics]

        assert 'system.net.bytes_rcvd' in metric_names
        assert 'system.net.bytes_sent' in metric_names
        if Platform.is_linux():
            assert 'system.net.tcp.retrans_segs' in metric_names
            assert 'system.net.tcp.in_segs' in metric_names
            assert 'system.net.tcp.out_segs' in metric_names
        elif Platform.is_bsd():
            assert 'system.net.tcp.retrans_packs' in metric_names
            assert 'system.net.tcp.sent_packs' in metric_names
            assert 'system.net.tcp.rcv_packs' in metric_names
