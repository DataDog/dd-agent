# 3rd party
from nose.plugins.attrib import attr

# Agent
from checks import AgentCheck
from tests.checks.common import AgentCheckTest


@attr(requires='gearman')
class GearmanTestCase(AgentCheckTest):
    CHECK_NAME = "gearmand"

    def test_metrics(self):
        tags = ['first_tag', 'second_tag']
        service_checks_tags = ['server:127.0.0.1', 'port:4730']
        config = {
            'instances': [{
                'tags': tags
            }]
        }
        tags += service_checks_tags
        self.run_check(config)
        self.assertMetric('gearman.unique_tasks', value=0.0, tags=tags, count=1)
        self.assertMetric('gearman.running', value=0.0, tags=tags, count=1)
        self.assertMetric('gearman.queued', value=0.0, tags=tags, count=1)
        self.assertMetric('gearman.workers', value=0.0, tags=tags, count=1)

        self.assertServiceCheck("gearman.can_connect", status=AgentCheck.OK,
            tags=service_checks_tags, count=1)
        self.coverage_report()


    def test_service_checks(self):
        config = {
            'instances': [
                {'host': '127.0.0.1', 'port': 4730},
                {'host': '127.0.0.1', 'port': 4731}]
        }

        self.assertRaises(Exception, self.run_check, config)
        service_checks_tags_ok = ['server:127.0.0.1', 'port:4730']
        service_checks_tags_not_ok = ['server:127.0.0.1', 'port:4731']

        tags = service_checks_tags_ok

        self.assertMetric('gearman.unique_tasks', value=0.0, tags=tags, count=1)
        self.assertMetric('gearman.running', value=0.0, tags=tags, count=1)
        self.assertMetric('gearman.queued', value=0.0, tags=tags, count=1)
        self.assertMetric('gearman.workers', value=0.0, tags=tags, count=1)
        self.assertServiceCheck("gearman.can_connect", status=AgentCheck.OK,
            tags=service_checks_tags_ok, count=1)
        self.assertServiceCheck("gearman.can_connect", status=AgentCheck.CRITICAL,
            tags=service_checks_tags_not_ok, count=1)

        self.coverage_report()
