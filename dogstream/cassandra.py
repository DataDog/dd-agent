from datetime import datetime
import re

from dogstream import common

LOG4J_PRIORITY = [
    "TRACE",
    "DEBUG",
    "INFO",
    "WARN",
    "ERROR",
    "FATAL",
]

ALERT_TYPES = {
    "FATAL": "error",
    "ERROR": "error",
    "WARN": "warning",
    "INFO": "info",
    "DEBUG": "info",
    "TRACE": "info",
}

EVENT_TYPE = "cassandra.compaction"

THREADS = [
    "CompactionExecutor",
]

DATE_FORMAT = '%Y-%m-%d %H:%M:%S,%f'

LOG_PATTERN = re.compile(r"".join([
    r"\s*(?P<priority>%s)\s+" % "|".join("(%s)" % p for p in LOG4J_PRIORITY),
    r"(\[CompactionExecutor:\d*\])?\s*", # thread name and number
    r"((?P<timestamp>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2},\d*)|",
        r"(?P<time>\d{2}:\d{2}:\d{2},\d*))\s+",
    r"(?P<msg>Compact(ed|ing) .*)\s*",
]))


def parse_cassandra(log, line):
    matched = LOG_PATTERN.match(line)
    if matched:
        event = matched.groupdict()

        # Convert the timestamp string into an epoch timestamp
        time_val = event.get('time', None)
        if time_val:
            event['timestamp'] = common.parse_date("%s %s" % (datetime.utcnow().strftime("%Y-%m-%d"), time_val), DATE_FORMAT)
        else:
            event['timestamp'] = common.parse_date(event['timestamp'], DATE_FORMAT)
        del event['time']

        # Process the log priority
        event['alert_type'] = ALERT_TYPES.get(event['priority'], "info")
        del event['priority']

        # Process the aggregation metadata
        event['event_type'] = EVENT_TYPE

        # Process the message
        msg = event['msg']
        if len(msg) > common.MAX_TITLE_LEN:
            event['msg_title'] = msg[0:common.MAX_TITLE_LEN]
            event['msg_text'] = msg
        else:
            event['msg_title'] = msg
        del event['msg']

        return [event]
    else:
        return None
