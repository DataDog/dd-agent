class OperationalError(Exception): pass

class MockSql(object):
    "Pretends to be a MySQL db"
    def __init__(self):
        self.answers = {"SELECT VERSION()": ("5.1.46", ),
                        "SHOW STATUS LIKE 'Connections'": 1,
                        "SHOW GLOBAL STATUS LIKE 'Created_tmp_disk_tables": 2,
                        "SHOW GLOBAL STATUS LIKE 'Slow_queries'": 3,
                        "SHOW GLOBAL STATUS LIKE 'Questions'": 4,
                        "SHOW STATUS LIKE 'Max_used_connections'": 5,
                        "SHOW STATUS LIKE 'Open_files'": 6,
                        "SHOW STATUS LIKE 'Table_locks_waited'": 7,
                        "SHOW STATUS LIKE 'Threads_connected'": 8,
                        "SHOW SLAVE STATUS": {"Seconds_behind_master": 9}}
        self.result = None # to be returned by fetch

    def cursor(self):
        return self

    def execute(self, query):
        self.result = self.answers[query]
        print query

    def fetchone(self):
        print self.result
        return self.result

m = MockSql()
def connect(*args):
    return m
