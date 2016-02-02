#!/bin/bash

set -e

if [ "$TEST_SUITE" == "unit" ]; then
  echo "Exiting, no integration tests"
  exit
fi
pushd $INTEGRATIONS_DIR/
arr=(${CASSANDRA_HOSTS//,/ })

pip install PyYAML six
git clone https://github.com/pcmanus/ccm.git
pushd ccm
./setup.py install
popd
ccm create test -v binary:$CASSANDRA_VERSION -n ${#arr[@]} -d
ccm start -v
ccm status
popd