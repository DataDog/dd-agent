#!/bin/bash

i=0
tests=()
exit_code=0
IFS=',' read -ra flavors <<< "$CIRCLECI_FLAVORS"
for flavor in $flavors
do
  if [ $(($i % $CIRCLE_NODE_TOTAL)) -eq $CIRCLE_NODE_INDEX ]
  then
    rake ci:run_circle[$flavor]
    if [[ $exit_code -ne 0 || $? -ne 0 ]] ; then
      exit_code=1
    fi
  fi
  ((i++))
done
exit $exit_code
