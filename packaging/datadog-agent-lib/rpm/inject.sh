#! /bin/sh

cat $1 | sed -e "/Requires:/ a\
Obsoletes: datadog-agent < 2.0" >! $1
