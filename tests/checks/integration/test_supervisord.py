# stdlib
import os
from time import sleep

# 3p
from nose.plugins.attrib import attr

# project
from checks import AgentCheck
from tests.checks.common import AgentCheckTest

PROCESSES = ["program_0", "program_1", "program_2"]
STATUSES = ["down", "up", "unknown"]


@attr(requires='supervisord')
class TestSupervisordCheck(AgentCheckTest):
    CHECK_NAME = 'supervisord'

    SUPERVISORD_CONFIG = [{
        'name': "travis",
        'socket': "unix://{0}//supervisor.sock".format(os.environ['VOLATILE_DIR']),
    }]

    BAD_SUPERVISORD_CONFIG = [{
        'name': "travis",
        'socket': "unix:///wrong/path/supervisor.sock",
        'host': "http://127.0.0.1",
    }]

    # Supervisord should run 3 programs for 10, 20 and 30 seconds
    # respectively.
    # The following dictionnary shows the processes by state for each iteration.
    PROCESSES_BY_STATE_BY_ITERATION = map(
        lambda x: dict(up=PROCESSES[x:], down=PROCESSES[:x], unknown=[]),
        range(4)
    )

    def test_check(self):
        """
        Run Supervisord check and assess coverage
        """
        config = {'instances': self.SUPERVISORD_CONFIG}
        instance_tags = ["supervisord_server:travis"]

        for i in range(4):
            # Run the check
            self.run_check(config)

            # Check metrics and service checks scoped by process
            for proc in PROCESSES:
                process_tags = instance_tags + ["supervisord_process:{0}".format(proc)]
                process_status = AgentCheck.OK if proc in \
                    self.PROCESSES_BY_STATE_BY_ITERATION[i]['up'] else AgentCheck.CRITICAL

                self.assertMetric("supervisord.process.uptime", tags=process_tags, count=1)
                self.assertServiceCheck("supervisord.process.status", status=process_status,
                                        tags=process_tags, count=1)
            # Check instance metrics
            for status in STATUSES:
                status_tags = instance_tags + ["status:{0}".format(status)]
                count_processes = len(self.PROCESSES_BY_STATE_BY_ITERATION[i][status])
                self.assertMetric("supervisord.process.count", value=count_processes,
                                  tags=status_tags, count=1)

            # Check service checks
            self.assertServiceCheck("supervisord.can_connect", status=AgentCheck.OK,
                                    tags=instance_tags, count=1)

            # Raises when coverage < 100%
            self.coverage_report()

            # Sleep 10s to give enough time to processes to terminate
            sleep(10)

    def test_connection_falure(self):
        """
        Service check reports connection failure
        """
        config = {'instances': self.BAD_SUPERVISORD_CONFIG}
        instance_tags = ["supervisord_server:travis"]

        self.assertRaises(
            Exception,
            lambda: self.run_check(config)
        )
        self.assertServiceCheck("supervisord.can_connect", status=AgentCheck.CRITICAL,
                                tags=instance_tags, count=1)
        self.coverage_report()
