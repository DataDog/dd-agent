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

# run agent
cd $dd_base
supervisord -c $dd_base/supervisord/supervisord.conf &> /dev/null &
agent_pid=$!
trap "{ kill $agent_pid; exit 255; }" SIGINT SIGTERM
trap "{ kill $agent_pid; exit; }" EXIT

for [

# wait for metrics to be submitted
echo "\033[32m
Your agent has started for the first time as a test. Once we verify
that it's submitted data, well stop it. You should see it show up in
a few seconds at:

    https://app.datadoghq.com/account/settings#agent\033[0m

Waiting for metrics...\c"

c=0
while [ "$c" -lt "30" ]; do
    sleep 1
    echo ".\c"
    c=$(($c+1))
done

curl -f http://localhost:17123/status?threshold=0 &> /dev/null
success=$?
while [ "$success" -gt "0" ]; do
    sleep 1
    echo ".\c"
    curl -f http://localhost:17123/status?threshold=0 &> /dev/null
    success=$?
done

# print instructions
echo "\033[32m

Success! Your agent is functioning properly. To start it back up in
the foreground, run:

    cd $dd_base
    sh bin/agent
"

if [ "$unamestr" = "Darwin" ]; then
echo "To set it up as a daemon, run:

    mkdir -p ~/Library/LaunchAgents
    cp $dd_base/launchd/com.datadoghq.Agent.plist ~/Library/LaunchAgents/.
    launchctl load -w ~/Library/LaunchAgents/com.datadoghq.Agent.plist
"
fi

echo "\033[0m\c"
