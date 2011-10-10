#! /bin/sh

sed -i "/Requires:/ a\
Conflicts: datadog-agent < 2.0\n\
Conflicts: datadog-agent-base < 2.1.0\n" $1
