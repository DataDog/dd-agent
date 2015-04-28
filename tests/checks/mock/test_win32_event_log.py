import unittest
import logging
from nose.plugins.attrib import attr

from tests.checks.common import get_check

logging.basicConfig()

CONFIG = """
init_config:

instances:
    -   host: .
        tags:
            - testtag1
            - testtag2
        log_file:
            - Application
        source_name:
            - EVENTLOGTEST
        type:
            - Warning
        notify:
            - pagerduty
            - "user1@somecompany.com"

    -   host: .
        tags:
            - testtag1
            - testtag2
        log_file:
            - Application
        source_name:
            - EVENTLOGTEST
        type:
            - Error
            - Information
"""

class WinEventLogTest(unittest.TestCase):
    def setUp(self):
        import win32evtlog
        self.LOG_EVENTS = [
            ('Test 1', win32evtlog.EVENTLOG_WARNING_TYPE),
            ('Test 2', win32evtlog.EVENTLOG_ERROR_TYPE),
            ('Test 3', win32evtlog.EVENTLOG_INFORMATION_TYPE),
            ('Test 4', win32evtlog.EVENTLOG_WARNING_TYPE),
            ('Test 5', win32evtlog.EVENTLOG_WARNING_TYPE),
            ('Test 6', win32evtlog.EVENTLOG_ERROR_TYPE),
        ]

    def write_event(self, msg, ev_type, source_name='EVENTLOGTEST'):
        # Thanks to http://rosettacode.org/wiki/Write_to_Windows_event_log
        import win32api
        import win32con
        import win32security
        import win32evtlogutil

        ph = win32api.GetCurrentProcess()
        th = win32security.OpenProcessToken(ph, win32con.TOKEN_READ)
        my_sid = win32security.GetTokenInformation(th, win32security.TokenUser)[0]

        applicationName = source_name
        eventID = 1
        category = 5
        myType = ev_type
        descr = [msg, msg]
        data = "Application\0Data".encode("ascii")

        win32evtlogutil.ReportEvent(applicationName, eventID, eventCategory=category,
            eventType=myType, strings=descr, data=data, sid=my_sid)

    @attr('windows')
    def test_windows_event_log(self):
        import win32evtlog
        check, instances = get_check('win32_event_log', CONFIG)

        # Run the check against all instances to set the last_ts
        for instance in instances:
            check.check(instance)

        # Run checks again and make sure there are no events
        for instance in instances:
            check.check(instance)
            assert len(check.get_metrics()) == 0

        # Generate some events for the log
        for msg, ev_type in self.LOG_EVENTS:
            self.write_event(msg, ev_type)
        self.write_event('do not pick me', win32evtlog.EVENTLOG_INFORMATION_TYPE,
            source_name='EVENTLOGTESTBAD')

        # Run the checks again for them to pick up the new events
        inst1, inst2 = instances
        check.check(inst1)
        ev1 = check.get_events()
        assert len(ev1) > 0
        assert len(ev1) == len([ev for ev in self.LOG_EVENTS
            if ev[1] == win32evtlog.EVENTLOG_WARNING_TYPE])
        for ev in ev1:
            # Make sure we only picked up our source
            assert 'EVENTLOGTESTBAD' not in ev['msg_title']
            # Make sure the tags match up
            assert ev['tags'] == inst1['tags']
            # Check that the notifications are there.
            for notify in inst1['notify']:
                assert '@%s' % notify in ev['msg_text']

        check.check(inst2)
        ev2 = check.get_events()
        assert len(ev2) > 0
        assert len(ev2) == len([ev for ev in self.LOG_EVENTS
            if ev[1] in (win32evtlog.EVENTLOG_ERROR_TYPE, win32evtlog.EVENTLOG_INFORMATION_TYPE)])
        for ev in ev2:
            # Make sure we only picked up our source
            assert 'EVENTLOGTESTBAD' not in ev['msg_title']
            # Make sure the tags match up
            assert ev['tags'] == inst1['tags']


if __name__ == "__main__":
    unittest.main()
