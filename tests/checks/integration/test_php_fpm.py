# 3p
from nose.plugins.attrib import attr

# project
from checks import AgentCheck
from tests.checks.common import AgentCheckTest

# sample from /status?json
#  {
#     "accepted conn": 350,
#     "active processes": 1,
#     "idle processes": 2,
#     "listen queue": 0,
#     "listen queue len": 0,
#     "max active processes": 2,
#     "max children reached": 0,
#     "max listen queue": 0,
#     "pool": "www",
#     "process manager": "dynamic",
#     "slow requests": 0,
#     "start since": 4758,
#     "start time": 1426601833,
#     "total processes": 3
# }


@attr(requires='phpfpm')
class PHPFPMCheckTest(AgentCheckTest):
    CHECK_NAME = 'php_fpm'

    def test_bad_status(self):
        instance = {
            'status_url': 'http://localhost:9001/status',
            'tags': ['expectedbroken']
        }

        self.assertRaises(Exception, self.run_check, {'instances': [instance]})

    def test_bad_ping(self):
        instance = {
            'ping_url': 'http://localhost:9001/status',
            'tags': ['expectedbroken']
        }

        self.run_check({'instances': [instance]})
        self.assertServiceCheck(
            'php_fpm.can_ping',
            status=AgentCheck.CRITICAL,
            tags=['ping_url:http://localhost:9001/status'],
            count=1
        )

        self.coverage_report()

    def test_bad_ping_reply(self):
        instance = {
            'ping_url': 'http://localhost:42424/ping',
            'ping_reply': 'blah',
            'tags': ['expectedbroken']
        }

        self.run_check({'instances': [instance]})
        self.assertServiceCheck(
            'php_fpm.can_ping',
            status=AgentCheck.CRITICAL,
            tags=['ping_url:http://localhost:42424/ping'],
            count=1
        )

        self.coverage_report()

    def test_status(self):
        instance = {
            'status_url': 'http://localhost:42424/status',
            'ping_url': 'http://localhost:42424/ping',
            'tags': ['cluster:forums']
        }

        self.run_check_twice({'instances': [instance]})

        metrics = [
            'php_fpm.listen_queue.size',
            'php_fpm.processes.idle',
            'php_fpm.processes.active',
            'php_fpm.processes.total',
            'php_fpm.requests.slow',
            'php_fpm.requests.accepted',
        ]

        expected_tags = ['cluster:forums', 'pool:www']

        for mname in metrics:
            self.assertMetric(mname, count=1, tags=expected_tags)

        self.assertMetric('php_fpm.processes.idle', count=1, value=1)
        self.assertMetric('php_fpm.processes.total', count=1, value=2)

        self.assertServiceCheck('php_fpm.can_ping', status=AgentCheck.OK,
                                count=1,
                                tags=['ping_url:http://localhost:42424/ping'])

        self.assertMetric('php_fpm.processes.max_reached', count=1)
