# 3p
from nose.plugins.attrib import attr

# project
from tests.checks.common import AgentCheckTest


@attr(requires='linuxvm')
class TestLinuxVm(AgentCheckTest):
    CHECK_NAME = 'linuxvm'

    def test_checks(self):
        config = {
            'init_config': {},
            'instances': [
                {
                    'vmstat': {
                        'gauges': [
                            'nr_free_pages',
                            'nr_alloc_batch',
                            'nr_inactive_anon',
                            'nr_active_anon'
                        ],
                        'counts': [
                            'pgpgin',
                            'pgpgout',
                            'pswpin',
                            'pswpout'
                        ]
                    }
                }
            ]
        }

        self.run_check_twice(config)
        metrics = config['instances'][0]['vmstat']
        [self.assertMetric('system.vm.' + m) for m in metrics['gauges'] + metrics['counts']]
