import os
import time
import unittest

from tests.common import get_check


class VarnishTestCase(unittest.TestCase):
    def setUp(self):
        varnish_dump_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'varnish')
        self.v_dump = open(os.path.join(varnish_dump_dir, 'v_dump'), 'r').read()

        self.xml_dump = open(os.path.join(varnish_dump_dir, 'dump.xml'), 'r').read()

        self.varnishadm_dump = open(os.path.join(varnish_dump_dir, 'varnishadm_dump'), 'r').read()

        self.config = """
instances:
    -   varnishstat: /usr/bin/varnishstat
"""

    def test_parsing(self):
        v, instances = get_check('varnish', self.config)
        v._parse_varnishstat(self.v_dump, False)
        metrics = v.get_metrics()
        self.assertEquals([m[2] for m in metrics
                          if m[0] == "varnish.n_waitinglist"][0], 980)
        assert "varnish.fetch_length" not in [m[0] for m in metrics]

        # XML parsing
        v._parse_varnishstat(self.xml_dump, True)
        metrics = v.get_metrics()
        self.assertEquals([m[2] for m in metrics
                          if m[0] == "varnish.SMA.s0.g_space"][0], 120606)
        assert "varnish.SMA.transient.c_bytes" not in [m[0] for m in metrics]

    def test_check(self):
        v, instances = get_check('varnish', self.config)
        import pprint
        try:
            for i in range(3):
                v.check({"varnishstat": os.popen("which varnishstat").read()[:-1]})
                pprint.pprint(v.get_metrics())
                time.sleep(1)
        except Exception:
            pass

    def test_service_check(self):

        v, instances = get_check('varnish', self.config)
        v._parse_varnishadm(self.varnishadm_dump)
        service_checks = v.get_service_checks()
        self.assertEquals(len(service_checks), 2)

        b0_check = service_checks[0]
        self.assertEquals(b0_check['check'], v.SERVICE_CHECK_NAME)
        self.assertEquals(b0_check['tags'], ['backend:b0'])

        b1_check = service_checks[1]
        self.assertEquals(b1_check['check'], v.SERVICE_CHECK_NAME)
        self.assertEquals(b1_check['tags'], ['backend:b1'])

if __name__ == '__main__':
    unittest.main()
