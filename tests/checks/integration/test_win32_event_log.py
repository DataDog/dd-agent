# stdlib
import time

# 3p
from nose.plugins.attrib import attr

# project
from tests.checks.common import AgentCheckTest
from utils.platform import Platform

# Not beautiful, to avoid failures on Linux
if Platform.is_windows():
    import win32api
    import win32con
    import win32evtlog
    import win32evtlogutil
    import win32security


INSTANCE_WARN = {
    'tags': ['testtag1', 'testtag2'],
    'log_file': ['Application'],
    'source_name': ['DDEVENTLOGTEST'],
    'type': ['Warning']
}
INSTANCE_ERR_INFO = {
    'tags': ['testtag3'],
    'log_file': ['Application'],
    'source_name': ['DDEVENTLOGTEST'],
    'type': ['Error', 'Information']
}


@attr('windows')
@attr(requires='windows')
class WinEventLogTest(AgentCheckTest):
    CHECK_NAME = 'win32_event_log'

    def setUp(self):
        self.LOG_EVENTS = [
            ('Test 1', win32evtlog.EVENTLOG_WARNING_TYPE),
            ('Test 2', win32evtlog.EVENTLOG_ERROR_TYPE),
            ('Test 3', win32evtlog.EVENTLOG_INFORMATION_TYPE),
            ('Test 4', win32evtlog.EVENTLOG_WARNING_TYPE),
            ('Test 4', win32evtlog.EVENTLOG_WARNING_TYPE),
            ('Test 6', win32evtlog.EVENTLOG_ERROR_TYPE),
        ]

    # Writes all events now to be sure all tests have them
    def write_events(self):
        for msg, ev_type in self.LOG_EVENTS:
            self.write_event(msg, ev_type)
        self.write_event('do not pick me', win32evtlog.EVENTLOG_INFORMATION_TYPE,
                         source_name='EVENTLOGTESTBAD')

    # Thanks to http://rosettacode.org/wiki/Write_to_Windows_event_log
    def write_event(self, msg, ev_type, source_name='DDEVENTLOGTEST'):
        if not hasattr(self, '_my_sid'):
            ph = win32api.GetCurrentProcess()
            th = win32security.OpenProcessToken(ph, win32con.TOKEN_READ)
            self._my_sid = win32security.GetTokenInformation(th, win32security.TokenUser)[0]

        win32evtlogutil.ReportEvent(
            source_name,
            1,
            eventCategory=5,
            eventType=ev_type,
            strings=[msg],
            data="Application\0Data".encode("ascii"),
            sid=self._my_sid
        )

    def assertEvent(self, msg_text, alert_type=None, count=None, tags=None):
        AgentCheckTest.assertEvent(
            self, msg_text, alert_type=alert_type, count=count, tags=tags,
            aggregation_key='DDEVENTLOGTEST', event_type='win32_log_event',
            source_type_name='event viewer', msg_title='Application/DDEVENTLOGTEST'
        )

    def test_no_event(self):
        self.run_check_twice({'instances': [INSTANCE_WARN, INSTANCE_ERR_INFO]},
                             force_reload=True)
        self.coverage_report()

    def test_windows_err_info_event_log(self):
        self.run_check({'instances': [INSTANCE_ERR_INFO]}, force_reload=True)
        # We wait one sec because the first run only gets the original timestamp
        # from which events will be queried
        time.sleep(1)
        self.write_events()
        self.run_check({'instances': [INSTANCE_ERR_INFO]})
        self.assertEvent('Test 2', alert_type='error', tags=['testtag3'], count=1)
        self.assertEvent('Test 6', alert_type='error', tags=['testtag3'], count=1)
        self.assertEvent('Test 3', alert_type='info', tags=['testtag3'], count=1)
        self.coverage_report()

    def test_windows_warn_event_log(self):
        # tests are run following an alphabetical order, so this one follows
        # err_info_event, to avoid conflict with its events, we wait 1 sec
        time.sleep(1)
        self.run_check({'instances': [INSTANCE_WARN]}, force_reload=True)
        time.sleep(1)
        self.write_events()
        self.run_check({'instances': [INSTANCE_WARN]})
        self.assertEvent('Test 1', alert_type='warning', tags=['testtag1', 'testtag2'], count=1)
        self.assertEvent('Test 4', alert_type='warning', tags=['testtag1', 'testtag2'], count=2)
        self.coverage_report()
