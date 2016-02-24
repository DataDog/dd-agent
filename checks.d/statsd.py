# (C) Datadog, Inc. 2015-2016
# (C) Cory Watson <cory@stripe.com> 2015
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
import re
import socket
from StringIO import StringIO

# project
from checks import AgentCheck

SERVICE_CHECK_NAME = "statsd.can_connect"
SERVICE_CHECK_NAME_HEALTH = "statsd.is_up"

ENDER = re.compile("^(END|health: up|health: down)\n$", re.MULTILINE)
BAD_ENDER = re.compile("^ERROR\n$", re.MULTILINE)

class StatsCheck(AgentCheck):
    def check(self, instance):
        host = instance.get("host", "localhost")
        port = instance.get("port", 8126)
        tags = instance.get("tags", [])
        tags = ["host:{0}".format(host), "port:{0}".format(port)] + tags

        # Is it up?
        health = self._send_command(host, port, "health", tags).getvalue().strip()
        if health == "health: up":
            self.service_check(
                SERVICE_CHECK_NAME_HEALTH, AgentCheck.OK, tags
            )
        else:
            self.service_check(
                SERVICE_CHECK_NAME_HEALTH, AgentCheck.CRITICAL, tags
            )

        # Get general stats
        stats = self._send_command(host, port, "stats", tags)
        stats.seek(0)
        for l in stats.readlines():
            parts = l.strip().split(":")
            if len(parts) == 2:
                # Uptime isn't a gauge. Since we have only one exception, this
                # seems fine. If we make more a lookup table might be best.
                if parts[0] == "bad_lines_seen":
                    self.monotonic_count("statsd.{0}".format(parts[0]), float(parts[1]), tags=tags)
                else:
                    self.gauge("statsd.{0}".format(parts[0]), float(parts[1]), tags=tags)

        counters = len(self._send_command(host, port, "counters", tags).getvalue().splitlines()) - 1
        self.gauge("statsd.counters.count", counters, tags=tags)

        gauges = len(self._send_command(host, port, "gauges", tags).getvalue().splitlines()) - 1
        self.gauge("statsd.gauges.count", gauges, tags=tags)

        timers = len(self._send_command(host, port, "timers", tags).getvalue().splitlines()) - 1
        self.gauge("statsd.timers.count", timers, tags=tags)

        # Send the final service check status
        self.service_check(SERVICE_CHECK_NAME, AgentCheck.OK, tags)

    def _send_command(self, host, port, command, tags):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((host, port))

            s.sendall("{0}\n".format(command))

            buf = StringIO()

            chunk = s.recv(1024)
            buf.write(chunk)
            while chunk:
                if ENDER.search(chunk):
                    break
                if BAD_ENDER.search(chunk):
                    raise Exception("Got an error issuing command: {0}".format(command))
                chunk = s.recv(1024)
                buf.write(chunk)
            return buf
        except Exception as e:
            self.service_check(
                SERVICE_CHECK_NAME, AgentCheck.CRITICAL, tags
            )
            raise Exception("Failed connection {0}".format(str(e)))
        finally:
            s.close()
