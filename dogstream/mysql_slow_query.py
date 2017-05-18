"""
Dogstream parser for mysql slow query log

This Dogstream requires slow query log to be enabled
in mysql server my.cnf
```
# /etc/mysql/my.cnf
log_slow_queries        = /var/log/mysql/mysql-slow.log
long_query_time         = 2
```

Must also enable this customer log parser in datadog.conf

```
# /etc/dd-agent/datadog.conf
dogstreams: /var/log/mysql/mysql-slow.log:/opt/datadog-agent/agent/dogstream/mysql_slow_query.py:parse_slow_query
```

The outputted events will look like:

title:
  Slow query from root[root]@localhost
text:
  # Time: 140923 22:26:00
  # User@Host: root[root] @ localhost []
  # Query_time: 4.000194 Lock_time: 0.000000 Rows_sent: 1 Rows_examined: 0
  SET timestamp=1411525560;
  select sleep(4);
"""
import json
import re
import time

STARTING_LINE = re.compile(r"# Time:")
SCHEMA_PATTERN = re.compile(r"Schema: ([^\s]+)")
HOSTNAME_PATTERN = re.compile(r"# User@Host: ([^\s]+)\s+@\s+([^\s]+)")
TIME_PATTERN = re.compile(r"# Time: (.*)")
TIMESTAMP_PATTERN = re.compile(r"SET timestamp=([0-9]+)")
CURRENT_QUERY = ""


def parse_event(query):
    # sometimes we get extra logging or startup info
    # from mysql in the log, so this makes sure we
    # have what we are looking for first
    if not STARTING_LINE.search(query):
        return None

    # we want to try and parse the selected database
    # the line looks something like:
    # "# Thread_id: 343  Schema: database_name  Last_errno: 0  Killed: 0"
    schema_match = SCHEMA_PATTERN.search(query)
    if schema_match:
        schema_name = schema_match.group(1)
    else:
        schema_name = "unknown"

    # this will parse out the connected user and host
    # the line will look like:
    # "# User@Host: user[user] @  [127.0.0.1]"
    # what we parse out and use is "user[user] @  [127.0.0.1]"
    hostname_match = HOSTNAME_PATTERN.search(query)
    user = hostname_match.group(1)
    host = hostname_match.group(2)

    # time can come from a few places
    # 1) from "SET timestamp=<UNIX_TIMESTAMP>;" line
    # 2) from "# Time: YYMMDD HH:MM:SS" starting line
    # 3) current unix timestamp
    timestamp_match = TIMESTAMP_PATTERN.search(query)
    timestamp = time.time()
    if timestamp_match:
        timestamp = int(timestamp_match.group(1))
    else:
        time_match = TIME_PATTERN.search(query)
        if time_match:
            timestamp = time_match.group(1)
            timestamp = int(time.mktime(time.strptime(timestamp, "%y%m%d %H:%M:%S")))

    return {
        "msg_title": "Slow query from %s@%s" % (user, host),
        "timestamp": timestamp,
        "msg_text": query,
        "alert_type": "warning",
        "event_type": "mysql.slow_query",
        "aggregation_key": "%s %s@%s" % (schema_name, user, host),
        "source_type_name": "mysql",
    }


def parse_slow_query(log, line):
    global CURRENT_QUERY
    event = None

    # if we have lines and reach a new query, this is an edge
    # case for if the query did not end in ";" or we missed it
    if STARTING_LINE.search(line) and CURRENT_QUERY:
        event = parse_event(CURRENT_QUERY)
        CURRENT_QUERY = ""

    if CURRENT_QUERY:
        CURRENT_QUERY += "\r\n"
    CURRENT_QUERY += line

    # if we have an ending query but it is not
    # "SET timestamp=<UNIX_TIMESTAMP>;"
    if ";" in line and not TIMESTAMP_PATTERN.search(line):
        event = parse_event(CURRENT_QUERY)
        CURRENT_QUERY = ""

    if event:
        import json
        print json.dumps(event)
    return event


if __name__ == "__main__":
    import sys
    import pprint
    import logging

    logging.basicConfig()
    log = logging.getLogger()
    with open(sys.argv[1]) as lines:
        events = (parse_slow_query(log, line) for line in lines)
        pprint.pprint([event for event in events if event is not None])
