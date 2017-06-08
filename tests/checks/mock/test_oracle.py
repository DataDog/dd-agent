# stdlib
import logging
from types import ListType
import unittest

# project
from tests.checks.common import get_check

logging.basicConfig()

"""
Uses Oracle instance running in VM from:
https://atlas.hashicorp.com/woznial/boxes/centos-6.3-oracle-xe

Include following line in your Vagrantfile:

config.vm.network "forwarded_port", guest: 1521, host: 8521

Using the "system" user as permission granting not available
for default "system" user

Install oracle instant client in /opt/oracle

Set up Oracle instant client:
http://jasonstitt.com/cx_oracle_on_os_x

Set:
export ORACLE_HOME=/opt/oracle/instantclient_12_1/
export DYLD_LIBRARY_PATH="$ORACLE_HOME:$DYLD_LIBRARY_PATH"
"""

CONFIG = """
init_config:

instances:
    -   server: 127.0.0.1:8521
        user: system
        password: manager
"""


class OracleTestCase(unittest.TestCase):
    def testOracle(self):
        check, instances = get_check('oracle', CONFIG)
        check.check(instances[0])
        metrics = check.get_metrics()

        # Make sure the base metrics loaded
        base_metrics = check.SYS_METRICS.values()
        ret_metrics = [m[0] for m in metrics]
        for metric in base_metrics:
            assert metric in ret_metrics

        service_checks = check.get_service_checks()
        service_checks_count = len(service_checks)
        self.assertTrue(isinstance(metrics, ListType))
        self.assertTrue(service_checks_count > 0)
        self.assertEquals(len([sc for sc in service_checks if sc['check'] == check.SERVICE_CHECK_NAME]), 1, service_checks)
