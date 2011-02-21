class OperationalError(Exception): pass

class MockSql(object):
    "Pretends to be a MySQL db"
    def __init__(self):
        self.answers = {"SELECT VERSION()": ("5.1.46", ),
                        "SHOW STATUS LIKE 'Connections'": ('connection', 1),
                        "SHOW GLOBAL STATUS LIKE 'Created_tmp_disk_tables'": ('tmp_tables', 2),
                        "SHOW GLOBAL STATUS LIKE 'Slow_queries'": ('slow_queries', 3),
                        "SHOW GLOBAL STATUS LIKE 'Questions'": ('questions', 4),
                        "SHOW STATUS LIKE 'Max_used_connections'": ('max_connections', 5),
                        "SHOW STATUS LIKE 'Open_files'": ('open_files', 6),
                        "SHOW STATUS LIKE 'Table_locks_waited'": ('locks_waited', 7),
                        "SHOW STATUS LIKE 'Threads_connected'": ('threads_connected', 8),
                        "SHOW SLAVE STATUS": {"Seconds_behind_master": 9}}
        self.result = None # to be returned by fetch

    def cursor(self):
        return self

    def execute(self, query):
        self.result = self.answers[query]

    def fetchone(self):
        return self.result

    def close(self):
        pass

m = MockSql()
def connect(*args):
    return m
