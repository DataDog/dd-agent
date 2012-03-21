class OperationalError(Exception): pass

class MockSql(object):
    "Pretends to be a MySQL db"
    def __init__(self):
        # Slave-specfic data
        self.description = (('Slave_IO_State',), ('Master_Host',), ('Master_User',), ('Master_Port',), ('Connect_Retry',), ('Master_Log_File',), ('Read_Master_Log_Pos',), ('Relay_Log_File',), ('Relay_Log_Pos',), ('Relay_Master_Log_File',), ('Slave_IO_Running',), ('Slave_SQL_Running',), ('Replicate_Do_DB',), ('Replicate_Ignore_DB',), ('Replicate_Do_Table',), ('Replicate_Ignore_Table',), ('Replicate_Wild_Do_Table',), ('Replicate_Wild_Ignore_Table',), ('Last_Errno',), ('Last_Error',), ('Skip_Counter',), ('Exec_Master_Log_Pos',), ('Relay_Log_Space',), ('Until_Condition',), ('Until_Log_File',), ('Until_Log_Pos',), ('Master_SSL_Allowed',), ('Master_SSL_CA_File',), ('Master_SSL_CA_Path',), ('Master_SSL_Cert',), ('Master_SSL_Cipher',), ('Master_SSL_Key',), ('Seconds_Behind_Master',), ('Master_SSL_Verify_Server_Cert',), ('Last_IO_Errno',), ('Last_IO_Error',), ('Last_SQL_Errno',), ('Last_SQL_Error',), ('Replicate_Ignore_Server_Ids',), ('Master_Server_Id',))
        self.slave = ('Waiting for master to send event', '82.94.171.107', 'replication', '3306', '60', 'mysql-bin.010160', '86026925', 'mysqld-relay-bin.019897', '86027071', 'mysql-bin.010160', 'Yes', 'Yes', None, None, None, None, None, None, '0', None, '0', '86026925', '86027173', None, None, '0', 'No', None, None, None, None, None, '9', 'No', '0', None, '0', None, None, '10')

        self.answers = {"SELECT VERSION()": ("5.1.46", ),
                        "SHOW STATUS LIKE 'Connections'": ('connection', 1),
                        "SHOW GLOBAL STATUS LIKE 'Created_tmp_disk_tables'": ('tmp_tables', 2),
                        "SHOW GLOBAL STATUS LIKE 'Slow_queries'": ('slow_queries', 3),
                        "SHOW GLOBAL STATUS LIKE 'Questions'": ('questions', 4),
                        "SHOW STATUS LIKE 'Max_used_connections'": ('max_connections', 5),
                        "SHOW STATUS LIKE 'Open_files'": ('open_files', 6),
                        "SHOW STATUS LIKE 'Table_locks_waited'": ('locks_waited', 7),
                        "SHOW STATUS LIKE 'Threads_connected'": ('threads_connected', 8),
                        "SHOW SLAVE STATUS": self.slave}
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
