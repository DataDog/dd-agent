#!/bin/sh

PATH=/opt/datadog-agent/embedded/bin:/opt/datadog-agent/bin:$PATH

exec /opt/datadog-agent/bin/supervisord -c /etc/dd-agent/supervisor.conf
