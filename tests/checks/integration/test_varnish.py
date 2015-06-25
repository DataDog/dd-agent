# 3p
from nose.plugins.attrib import attr

# project
from tests.checks.common import AgentCheckTest, Fixtures
from utils.shell import which


def mocked_varnishstatoutput(cmd):
    return Fixtures.read_file('dump.xml')


COMMON_METRICS = [
    'varnish.SMA.Transient.g_alloc',
    'varnish.SMA.Transient.g_bytes',
    'varnish.SMA.Transient.g_space',
    'varnish.VBE.default_127.0.0.1_4242.vcls',
    'varnish.n_backend',
    'varnish.n_expired',
    'varnish.n_lru_moved',
    'varnish.n_lru_nuked',
    'varnish.n_object',
    'varnish.n_objectcore',
    'varnish.n_objecthead',
    'varnish.n_vampireobject',
    'varnish.n_waitinglist',
    'varnish.sms_balloc',
    'varnish.sms_bfree',
    'varnish.sms_nbytes',
    'varnish.sms_nobj',
    'varnish.vmods',
]

METRICS_4_X = [
    'varnish.MEMPOOL.busyobj.live',
    'varnish.MEMPOOL.busyobj.pool',
    'varnish.MEMPOOL.busyobj.sz_needed',
    'varnish.MEMPOOL.busyobj.sz_wanted',
    'varnish.MEMPOOL.req0.live',
    'varnish.MEMPOOL.req0.pool',
    'varnish.MEMPOOL.req0.sz_needed',
    'varnish.MEMPOOL.req0.sz_wanted',
    'varnish.MEMPOOL.req1.live',
    'varnish.MEMPOOL.req1.pool',
    'varnish.MEMPOOL.req1.sz_needed',
    'varnish.MEMPOOL.req1.sz_wanted',
    'varnish.MEMPOOL.sess0.live',
    'varnish.MEMPOOL.sess0.pool',
    'varnish.MEMPOOL.sess0.sz_needed',
    'varnish.MEMPOOL.sess0.sz_wanted',
    'varnish.MEMPOOL.sess1.live',
    'varnish.MEMPOOL.sess1.pool',
    'varnish.MEMPOOL.sess1.sz_needed',
    'varnish.MEMPOOL.sess1.sz_wanted',
    'varnish.MEMPOOL.vbc.live',
    'varnish.MEMPOOL.vbc.pool',
    'varnish.MEMPOOL.vbc.sz_needed',
    'varnish.MEMPOOL.vbc.sz_wanted',
    'varnish.SMA.s0.g_alloc',
    'varnish.SMA.s0.g_bytes',
    'varnish.SMA.s0.g_space',
    'varnish.bans',
    'varnish.bans_completed',
    'varnish.bans_obj',
    'varnish.bans_persisted_bytes',
    'varnish.bans_persisted_fragmentation',
    'varnish.bans_req',
    'varnish.n_obj_purged',
    'varnish.n_purges',
    'varnish.pools',
    'varnish.thread_queue_len',
    'varnish.threads',
    'varnish.vsm_cooling',
    'varnish.vsm_free',
    'varnish.vsm_overflow',
    'varnish.vsm_used'
]

METRICS_3_X = [
    'varnish.n_ban',
    'varnish.n_ban_gone',
    'varnish.n_sess',
    'varnish.n_sess_mem',
    'varnish.n_vbc',
    'varnish.n_wrk',
    'varnish.SMF.s0.g_smf',
    'varnish.SMF.s0.g_bytes',
    'varnish.SMF.s0.g_space',
    'varnish.SMF.s0.g_smf_large',
    'varnish.SMF.s0.g_alloc',
    'varnish.SMF.s0.g_smf_frag',
]


@attr(requires='varnish')
class VarnishCheckTest(AgentCheckTest):
    CHECK_NAME = 'varnish'

    def test_check(self):
        varnishstat_path = which('varnishstat')
        self.assertTrue(varnishstat_path is not None, "Flavored testing should be run with a real varnish")

        config = {
            'instances': [{
                'varnishstat': varnishstat_path,
                'tags': ['cluster:webs']
            }]
        }

        self.run_check(config)
        version, _ = self.check._get_version_info(varnishstat_path)

        to_check = COMMON_METRICS
        if version == 3:
            to_check.extend(METRICS_3_X)
        elif version == 4:
            to_check.extend(METRICS_4_X)

        for mname in to_check:
            self.assertMetric(mname, count=1, tags=['cluster:webs', 'varnish_name:default'])

        self.coverage_report()
