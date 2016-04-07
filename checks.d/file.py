import errno
import os
import time

from checks import AgentCheck

class FileCheck(AgentCheck):

    STATUS_ABSENT = 'absent'
    STATUS_PRESENT = 'present'

    def __init__(self, name, init_config, agentConfig, instances=None):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances)
        self._last_state_by_path = {}

    def has_different_status(self, path, current):
        last_state = self._last_state_by_path.get(path, None)
        self._last_state_by_path[path] = current
        return (last_state is not None and last_state != current)

    def stat_file(self, path):
        try:
            statinfo = os.stat(path)
            return self.STATUS_PRESENT, statinfo
        except OSError, e:
            if e.errno == errno.ENOENT:
                return self.STATUS_ABSENT, []
            else:
                raise

    def check(self, instance):
        """
        Stats a file and emits service_checks and metrics on file creation/age.
        """
        if 'path' not in instance:
            raise Exception("Missing 'path' in file check config")
        if 'expect' not in instance:
            raise Exception("Missing 'expect' in file check config")

        path = instance['path']
        expect = instance['expect']

        status, statinfo = self.stat_file(path)

        tags = [
            'expected_status:' + expect,
            'path:' + path,
            'actual_status:' + status,
        ]

        # Emit a service check:
        msg = "File %s is %s" % (path, expect)
        check_status = AgentCheck.OK
        if status != expect:
            check_status = AgentCheck.CRITICAL
            msg = "File %s that was expected to be %s is %s instead" % (path, expect, status)
        self.service_check('file.existence', check_status, message=msg, tags=tags)

        # Emit an event if the previous state is known & it's different:
        if self.has_different_status(path, status):
            timestamp = time.time()
            if status == self.STATUS_PRESENT:
                timestamp = statinfo.st_ctime

            alert_type = 'success'
            if check_status != AgentCheck.OK:
                alert_type = 'error'

            title = 'File %s is now %s' % (path, status)
            self.event({
                'timestamp': timestamp,
                'event_type': 'file.presence_change',
                'msg_title': title,
                'alert_type': alert_type,
                'tags': tags,
                'aggregation_key': path,
            })

        # Emit age metrics (of dubious utility):
        file_age = -1
        if status == self.STATUS_PRESENT:
            file_age = time.time() - statinfo.st_ctime
        self.gauge('file.age_seconds', file_age, tags=tags)
