#! /bin/sh

cat $1
sed -i "/Requires:/ a\
Conflicts: datadog-agent < 2.0\n" $1
