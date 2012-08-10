#!/bin/sh

if [ -n "$DD_API_KEY" ]; then
    apikey=$DD_API_KEY
fi

unamestr=`uname`

if [ $(which curl) ]; then
    dl_cmd="curl -L -o"
else
    dl_cmd="wget -O"
fi

# create home base for the agent
if [ $apikey ]; then
    dd_base=$HOME/.datadog-agent
else
    dd_base=$HOME/.pup
fi
mkdir -p $dd_base

# set up a virtual env
$dl_cmd $dd_base/virtualenv.py https://raw.github.com/pypa/virtualenv/develop/virtualenv.py
python $dd_base/virtualenv.py $dd_base/venv
. $dd_base/venv/bin/activate

# install dependencies
pip install tornado
pip install argparse

# set up the agent
mkdir -p $dd_base/agent
$dl_cmd $dd_base/agent.tar.gz https://github.com/DataDog/dd-agent/tarball/merge-pup
tar -xz -C $dd_base/agent --strip-components 1 -f $dd_base/agent.tar.gz
if [ $apikey ]; then
    sed "s/api_key:.*/api_key: $apikey/" $dd_base/agent/datadog.conf.example > $dd_base/agent/datadog.conf.1
else
    sed "s/api_key:.*/api_key: pup/" $dd_base/agent/datadog.conf.example > $dd_base/agent/datadog.conf.1
fi
sed "s/# use_pup:.*/use_pup: yes/" $dd_base/agent/datadog.conf.1 > $dd_base/agent/datadog.conf
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
rm $dd_base/agent/datadog.conf.1

# run agent
cd $dd_base
supervisord -c $dd_base/supervisord/supervisord.conf > /dev/null 2>&1 &
agent_pid=$!
trap "{ kill $agent_pid; exit 255; }" INT TERM
trap "{ kill $agent_pid; exit; }" EXIT

# regular agent install
if [ $apikey ]; then

    # wait for metrics to be submitted
    echo "\033[32m
Your agent has started up for the first time. We're currently
verifying that data is being submitted. You should see your agent show
up in Datadog within a few seconds at:

    https://app.datadoghq.com/account/settings#agent\033[0m

Waiting for metrics...\c"

    c=0
    while [ "$c" -lt "30" ]; do
        sleep 1
        echo ".\c"
        c=$(($c+1))
    done

    curl -f http://localhost:17123/status?threshold=0 > /dev/null 2>&1
    success=$?
    while [ "$success" -gt "0" ]; do
        sleep 1
        echo ".\c"
        curl -f http://localhost:17123/status?threshold=0 > /dev/null 2>&1
        success=$?
    done

    # print instructions
    echo "\033[32m

Success! Your agent is functioning properly, and will continue to run
in the foreground. To stop it, simply press CTRL-C. To start it back
up again in the foreground, run:

cd $dd_base
sh bin/agent
"

    if [ "$unamestr" = "Darwin" ]; then
    echo "To set it up as a daemon that always runs in the background
while you're logged in, run:

    mkdir -p ~/Library/LaunchAgents
    cp $dd_base/launchd/com.datadoghq.Agent.plist ~/Library/LaunchAgents/.
    launchctl load -w ~/Library/LaunchAgents/com.datadoghq.Agent.plist
"
    fi

    echo "\033[0m\c"

# pup install
else

    # print instructions
    echo "\033[32m

Success! Pup is installed and functioning properly, and will continue to
run in the foreground. To stop it, simply press CTRL-C. To start it back
up again in the foreground, run:

    cd $dd_base
    sh bin/agent
"

    if [ "$unamestr" = "Darwin" ]; then
    echo "To set it up as a daemon that always runs in the background
while you're logged in, run:

    mkdir -p ~/Library/LaunchAgents
    cp $dd_base/launchd/com.datadoghq.Agent.plist ~/Library/LaunchAgents/.
    launchctl load -w ~/Library/LaunchAgents/com.datadoghq.Agent.plist
"
    fi

    echo "\033[0m\c"
fi

wait $agent_pid
