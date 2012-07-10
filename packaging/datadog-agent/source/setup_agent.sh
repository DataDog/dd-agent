#!/bin/sh

if [ $# -eq 1 ]; then
    apikey=$1
elif [ -n "$DD_API_KEY" ]; then
    apikey=$DD_API_KEY
else
    echo "Usage: $0 <api_key>"
    exit 1
fi

unamestr=`uname`

# create home base for the agent
dd_base=$HOME/.datadog-agent
mkdir -p $dd_base

# set up a virtual env
curl -L -o $dd_base/virtualenv.py https://raw.github.com/pypa/virtualenv/develop/virtualenv.py
python $dd_base/virtualenv.py --python=python2.6 $dd_base/venv
. $dd_base/venv/bin/activate

# install dependencies
pip install tornado

# set up the agent
mkdir -p $dd_base/agent
curl -L -o $dd_base/agent.tar.gz https://github.com/DataDog/dd-agent/tarball/master
tar -xz -C $dd_base/agent --strip-components 1 -f $dd_base/agent.tar.gz
sed "s/api_key:.*/api_key: $apikey/" $dd_base/agent/datadog.conf.example > $dd_base/agent/datadog.conf
mkdir -p $dd_base/bin
cp $dd_base/agent/packaging/datadog-agent/source/agent $dd_base/bin/agent
chmod +x $dd_base/bin/agent

# set up supervisor
mkdir -p $dd_base/supervisord/logs
pip install supervisor
cp $dd_base/agent/packaging/datadog-agent/source/supervisord.conf $dd_base/supervisord/supervisord.conf

if [ "$unamestr" = "Darwin" ]; then
    # prepare launchd
    mkdir -p $dd_base/launchd/logs
    touch $dd_base/launchd/logs/launchd.log
    sed "s|AGENT_BASE|$dd_base|; s|USER_NAME|$(whoami)|" $dd_base/agent/packaging/datadog-agent/osx/com.datadoghq.Agent.plist.example > $dd_base/launchd/com.datadoghq.Agent.plist
fi

# consolidate logging
mkdir -p $dd_base/logs
ln -s $dd_base/supervisord/logs $dd_base/logs/supervisord
if [ "$unamestr" = "Darwin" ]; then
    ln -s $dd_base/launchd/logs $dd_base/logs/launchd
fi

# clean up
rm $dd_base/virtualenv.py
rm $dd_base/virtualenv.pyc
rm $dd_base/agent.tar.gz

# print instructions
if [ "$unamestr" = "Darwin" ]; then
echo "

We're about to start up the agent for the first time. Once it's running,
you can stop it with 'ctrl-c'. You should start seeing metrics within
a few seconds at:

    https://app.datadoghq.com/dash/host_name/`hostname`

To start the agent up again after killing this script, run:

    cd $dd_base
    sh bin/agent

To make it permanent, run:

    mkdir -p ~/Library/LaunchAgents
    cp $dd_base/launchd/com.datadoghq.Agent.plist ~/Library/LaunchAgents/.
    launchctl load -w ~/Library/LaunchAgents/com.datadoghq.Agent.plist

Here we go!

"
fi

if [ "$unamestr" = "Linux" ]; then
echo "

We're about to start up the agent for the first time. Once it's running,
you can stop it with 'ctrl-c'. You should start seeing metrics within
a few seconds at:

    https://app.datadoghq.com/dash/host_name/`hostname`

To start the agent up again after killing this script, run:

    cd $dd_base
    sh bin/agent

Here we go!

"
fi

# run agent
cd $dd_base
supervisord -c $dd_base/supervisord/supervisord.conf
