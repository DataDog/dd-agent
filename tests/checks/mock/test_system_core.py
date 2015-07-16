import mock
import psutil

from tests.checks.common import AgentCheckTest
from utils.platform import Platform

if Platform.is_mac():
    CHECK_RATES = [
        'system.core.idle',
        'system.core.nice',
        'system.core.system',
        'system.core.user',
    ]
    MOCK_PSUTIL_CPU_TIMES = [
        psutil._psosx.scputimes(user=7877.29, nice=0.0, system=7469.72, idle=38164.81),
        psutil._psosx.scputimes(user=3826.74, nice=0.0, system=2701.6, idle=46981.39),
        psutil._psosx.scputimes(user=7486.51, nice=0.0, system=5991.36, idle=40031.88),
        psutil._psosx.scputimes(user=3964.85, nice=0.0, system=2862.37, idle=46682.5)
    ]
elif Platform.is_unix():
    CHECK_RATES = [
        'system.core.idle',
        'system.core.nice',
        'system.core.system',
        'system.core.user',
        'system.core.iowait',
        'system.core.irq',
        'system.core.softirq',
        'system.core.steal',
        'system.core.guest',
        'system.core.guest_nice',
    ]
    MOCK_PSUTIL_CPU_TIMES = [
        psutil._pslinux.scputimes(user=1805.64, nice=0.01, system=298.66, idle=14177.28,
                                  iowait=3.23, irq=0.05, softirq=33.28, steal=0.0,
                                  guest=0.0, guest_nice=0.0),
        psutil._pslinux.scputimes(user=1724.18, nice=0.04, system=235.61, idle=14381.94,
                                  iowait=3.55, irq=0.0, softirq=6.94, steal=0.0,
                                  guest=0.0, guest_nice=0.0),
        psutil._pslinux.scputimes(user=1737.58, nice=0.03, system=230.61, idle=14382.33,
                                  iowait=2.69, irq=0.0, softirq=6.12, steal=0.0,
                                  guest=0.0, guest_nice=0.0),
        psutil._pslinux.scputimes(user=1696.18, nice=0.0, system=218.36, idle=14610.06,
                                  iowait=2.43, irq=0.0, softirq=3.8, steal=0.0,
                                  guest=0.0, guest_nice=0.0)
    ]
else:
    MOCK_PSUTIL_CPU_TIMES = []

class SystemCoreTestCase(AgentCheckTest):

    CHECK_NAME = 'system_core'

    @mock.patch('psutil.cpu_times', return_value=MOCK_PSUTIL_CPU_TIMES)
    def test_system_core(self, mock_cpu_times):
        self.run_check_twice({"instances": [{}]})
        self.assertMetric('system.core.count', value=4, count=1)

        for i in range(4):
            for rate in CHECK_RATES:
                self.assertMetric(rate, count=1, tags=['core:{0}'.format(i)])

        self.coverage_report()
