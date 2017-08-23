#!/bin/sh
# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

PATH=/opt/datadog-agent/embedded/bin:/opt/datadog-agent/bin:$PATH

if [ "$DATADOG_ENABLED" = "no" ]; then
    echo "Disabled via DATADOG_ENABLED env var. Exiting."
    exit 0
fi

exec /opt/datadog-agent/bin/supervisord -c /etc/dd-agent/supervisor.conf
