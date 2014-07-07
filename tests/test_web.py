import unittest
import logging
import os
from nose.plugins.attrib import attr
logger = logging.getLogger(__file__)

from tests.common import get_check, read_data_from_file

class TestWeb(unittest.TestCase):

    def setUp(self):
        self.apache_config = """
init_config:

instances:
    -   apache_status_url: http://localhost:9444/server-status
        tags:
            - instance:first
    -   apache_status_url: http://localhost:9444/server-status?auto
        tags:
            - instance:second
"""

        self.nginx_config = """
init_config:

instances:
    -   nginx_status_url: http://localhost:44441/nginx_status/
    -   nginx_status_url: http://localhost:44441/nginx_status/
        tags:
            - first_one
    -   nginx_status_url: http://dummyurl:44441/nginx_status/
        tags:
            - dummy
    -   nginx_status_url: http://localhost:44441/nginx_status/
        tags:
            - second
"""

        self.lighttpd_config = """
init_config:

instances:
    -   lighttpd_status_url: http://localhost:9449/server-status
        tags:
            - instance:first
    -   lighttpd_status_url: http://localhost:9449/server-status?auto
        tags:
            - instance:second
"""

    def testApache(self):
        a, instances = get_check('apache', self.apache_config)

        a.check(instances[0])
        metrics = a.get_metrics()
        self.assertEquals(metrics[0][3].get('tags'), ['instance:first'])

        a.check(instances[1])
        metrics = a.get_metrics()
        self.assertEquals(metrics[0][3].get('tags'), ['instance:second'])

        service_checks = a.get_service_checks()
        can_connect = [sc for sc in service_checks if sc['check'] == 'apache.can_connect']
        for i in range(len(can_connect)):
            self.assertEquals(set(can_connect[i]['tags']), set(['host:localhost', 'port:9444']), service_checks)


    def testNginx(self):
        nginx, instances = get_check('nginx', self.nginx_config)
        nginx.check(instances[0])
        r = nginx.get_metrics()
        self.assertEquals(len([t for t in r if t[0] == "nginx.net.connections"]), 1, r)

        nginx.check(instances[1])
        r = nginx.get_metrics()
        self.assertEquals(r[0][3].get('tags'), ['first_one'])
        service_checks = r.get_service_checks()
        can_connect = [sc for sc in service_checks if sc['check'] == 'nginx.can_connect']
        for i in range(len(can_connect)):
            self.assertEquals(set(can_connect[i]['tags']), set(['host:localhost', 'port:44441']), service_checks)

    def testNginxPlus(self):
        test_data = read_data_from_file('nginx_plus_in.json')
        expected = eval(read_data_from_file('nginx_plus_out.python'))
        nginx, instances = get_check('nginx', self.nginx_config)
        parsed = nginx.parse_json(test_data)
        parsed.sort()
        self.assertEquals(parsed, expected)

    def testLighttpd(self):
        l, instances = get_check('lighttpd', self.lighttpd_config)

        l.check(instances[0])
        metrics = l.get_metrics()
        self.assertEquals(metrics[0][3].get('tags'), ['instance:first'])

        l.check(instances[1])
        metrics = l.get_metrics()
        self.assertEquals(metrics[0][3].get('tags'), ['instance:second'])
        service_checks = l.get_service_checks()
        service_checks = l.get_service_checks()
        can_connect = [sc for sc in service_checks if sc['check'] == 'lighttpd.can_connect']
        for i in range(len(can_connect)):
            self.assertEquals(set(can_connect[i]['tags']), set(['host:localhost', 'port:9449']), service_checks)


if __name__ == '__main__':
    unittest.main()
