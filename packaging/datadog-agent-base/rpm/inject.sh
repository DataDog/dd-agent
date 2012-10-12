#! /bin/sh

cat $1
sed -i "/Requires:/ a\
Conflicts: datadog-agent < 3.3\n" $1
