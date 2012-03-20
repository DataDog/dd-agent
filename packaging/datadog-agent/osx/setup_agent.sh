#!/bin/sh

if [ $# -ne 1 ]; then
    echo "Usage: $0 <api_key>"
    exit 1
fi

apikey=$1

## create home base for the agent
dd_base=$HOME/.datadog-agent
mkdir -p $dd_base

# set up a virtual env
curl -L -o $dd_base/virtualenv.py https://raw.github.com/pypa/virtualenv/master/virtualenv.py
python $dd_base/virtualenv.py --python=python2.6 $dd_base/venv
source $dd_base/venv/bin/activate

# install dependencies
pip install tornado

# set up the agent
mkdir -p $dd_base/agent
curl -L -o $dd_base/agent.tar.gz https://github.com/DataDog/dd-agent/tarball/master
tar -xz -C $dd_base/agent --strip-components 1 -f $dd_base/agent.tar.gz
sed "s/api_key:.*/api_key: $1/" $dd_base/agent/datadog.conf.example > $dd_base/agent/datadog.conf

# set up supervisor
mkdir -p $dd_base/supervisord/logs
pip install supervisor
cp $dd_base/agent/packaging/datadog-agent/osx/supervisord.conf $dd_base/supervisord/supervisord.conf

# clean up
rm $dd_base/virtualenv.py
rm $dd_base/agent.tar.gz
