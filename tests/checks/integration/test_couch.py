from checks import AgentCheck

from nose.plugins.attrib import attr

from tests.checks.common import AgentCheckTest


@attr(requires='couchdb')
class CouchTestCase(AgentCheckTest):

    CHECK_NAME = 'couch'

    # Publicly readable databases
    DB_NAMES = ['_users', '_replicator']

    # Databases required a logged in user
    RESTRICTED_DB_NAMES = ['kennel']

    GLOBAL_GAUGES = [
        'couchdb.couchdb.auth_cache_hits',
        'couchdb.couchdb.auth_cache_misses',
        'couchdb.httpd.requests',
        'couchdb.httpd_request_methods.GET',
        'couchdb.httpd_request_methods.PUT',
        'couchdb.couchdb.request_time',
        'couchdb.couchdb.open_os_files',
        'couchdb.couchdb.open_databases',
        'couchdb.httpd_status_codes.200',
        'couchdb.httpd_status_codes.201',
        'couchdb.httpd_status_codes.400',
        'couchdb.httpd_status_codes.401',
        'couchdb.httpd_status_codes.404',
    ]

    CHECK_GAUGES = [
        'couchdb.by_db.disk_size',
        'couchdb.by_db.doc_count',
    ]

    def __init__(self, *args, **kwargs):
        AgentCheckTest.__init__(self, *args, **kwargs)
        self.config = {"instances": [{"server": "http://localhost:5984"}]}

    def test_couch(self):
        self.run_check(self.config)

        # Metrics should have been emitted for any publicly readable databases.
        for db_name in self.DB_NAMES:
            tags = ['instance:http://localhost:5984', 'db:{0}'.format(db_name)]
            for gauge in self.CHECK_GAUGES:
                self.assertMetric(gauge, tags=tags, count=1)

        # No metrics should be available for any restricted databases as
        # we are querying anonymously
        for db_name in self.RESTRICTED_DB_NAMES:
            tags = ['instance:http://localhost:5984', 'db:{0}'.format(db_name)]
            for gauge in self.CHECK_GAUGES:
                self.assertMetric(gauge, tags=tags, count=0)

        # Check global metrics
        for gauge in self.GLOBAL_GAUGES:
            tags = ['instance:http://localhost:5984']
            self.assertMetric(gauge, tags=tags, at_least=0)

        self.assertServiceCheck(self.check.SERVICE_CHECK_NAME,
                                status=AgentCheck.OK,
                                tags=['instance:http://localhost:5984'],
                                count=1)

        self.coverage_report()

    def test_couch_authorized_user(self):
        self.config['instances'][0]['user'] = 'dduser'
        self.config['instances'][0]['password'] = 'pawprint'
        self.run_check(self.config)

        # As an authorized user we should be able to read restricted databases
        for db_name in self.RESTRICTED_DB_NAMES:
            tags = ['instance:http://localhost:5984', 'db:{0}'.format(db_name)]
            for gauge in self.CHECK_GAUGES:
                self.assertMetric(gauge, tags=tags, count=1)

    def test_bad_config(self):
        self.assertRaises(
            Exception,
            lambda: self.run_check({"instances": [{"server": "http://localhost:5985"}]})
        )

        self.assertServiceCheck(self.check.SERVICE_CHECK_NAME,
                                status=AgentCheck.CRITICAL,
                                tags=['instance:http://localhost:5985'],
                                count=1)

    def test_couch_whitelist(self):
        DB_WHITELIST = ["_users"]
        self.config['instances'][0]['db_whitelist'] = DB_WHITELIST
        self.run_check(self.config)
        for db_name in self.DB_NAMES:
            tags = ['instance:http://localhost:5984', 'db:{0}'.format(db_name)]
            for gauge in self.CHECK_GAUGES:
                if db_name in DB_WHITELIST:
                    self.assertMetric(gauge, tags=tags, count=1)
                else:
                    self.assertMetric(gauge, tags=tags, count=0)

    def test_couch_blacklist(self):
        DB_BLACKLIST = ["_replicator"]
        self.config['instances'][0]['db_blacklist'] = DB_BLACKLIST
        self.run_check(self.config)
        for db_name in self.DB_NAMES:
            tags = ['instance:http://localhost:5984', 'db:{0}'.format(db_name)]
            for gauge in self.CHECK_GAUGES:
                if db_name in DB_BLACKLIST:
                    self.assertMetric(gauge, tags=tags, count=0)
                else:
                    self.assertMetric(gauge, tags=tags, count=1)
