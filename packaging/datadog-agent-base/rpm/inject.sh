#! /bin/sh

cat $1 | sed -e "/Requires:/ a\
Conflicts: datadog-agent < 2.0\n" > $1
