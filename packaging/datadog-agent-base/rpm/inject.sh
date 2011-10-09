#! /bin/sh

sed -i "/Requires:/ a\
Conflicts: datadog-agent < 2.0\n" $1
