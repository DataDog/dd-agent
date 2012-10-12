#! /bin/sh

cat $1
sed -i "/Requires:/ a\
Conflicts: datadog-agent <= 3.2\n" $1
