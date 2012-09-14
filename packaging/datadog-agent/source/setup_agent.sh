#!/bin/sh
set -e

dogweb_reporting_failure_url="https://app.datadoghq.com/agent_stats/report_failure"
dogweb_reporting_success_url="https://app.datadoghq.com/agent_stats/report_success"
email_reporting_failure="help@datadoghq.com"
logfile="ddagent-install.log"

gist_request=/tmp/agent-gist-request.tmp
gist_response=/tmp/agent-gist-response.tmp

# Set up a named pipe for logging
npipe=/tmp/$$.tmp

function get_os() {
    # OS/Distro Detection
    if [ -f /etc/lsb-release ]; then
        . /etc/lsb-release
        OS=$DISTRIB_ID
    elif [ -f /etc/debian_version ]; then
        OS=Debian
    elif [ -f /etc/redhat-release ]; then
        # Just mark as RedHat and we'll use Python version detection
        # to know what to install
        OS=RedHat
    else
        OS=$(uname -s)
    fi
    if [ $OS = "Darwin" ]; then
        OS="MacOS"
    fi
}

get_os

if [ $OS = "MacOS" ]; then
    mkfifo $npipe
else
    mknod $npipe p
fi

# Log all output to a log for error checking
tee <$npipe $logfile &
exec 1>&-
exec 1>$npipe 2>&1

function report_using_mail() {
    if [ $? = 22 ]; then
        log=$(cat "$logfile")
        notfication_message_manual="\033[31m
    It looks like you hit an issue when trying to install the agent.

    Please send an email to help@datadoghq.com with the following content and any informations you think would be useful
    and we'll do our very best to help you solve your problem.

    Agent installation failure:
    OS: $OS
    Version: $agent_version
    Log: $log

    \n\033[0m"

        echo -e "Agent installation failure: \n OS: $OS \n Version: $agent_version \n\n Log:$log" | mail -s "Agent installation failure" $email_reporting_failure && echo -e "$notification_message" || echo -e "$notfication_message_manual"
        
    fi
    rm -f $npipe
    exit 1

}

trap report_using_mail EXIT

function get_api_key_to_report() {
    if [ $apikey ]; then
        key_to_report=$apikey
    else
        key_to_report="No_key"
    fi
}

function report_to_dogweb() {
    log=$(cat "$logfile")
    encoded_log=$(echo "$log" | python -c 'import sys, urllib; print urllib.quote(sys.stdin.read().strip())')
    OS=$(echo "$OS" | python -c 'import sys, urllib; print urllib.quote(sys.stdin.read().strip())')
    key_to_report=$(echo "$key_to_report" | python -c 'import sys, urllib; print urllib.quote(sys.stdin.read().strip())')
    agent_version=$(echo "$agent_version" | python -c 'import sys, urllib; print urllib.quote(sys.stdin.read().strip())')
    notification_message="\033[31m
It looks like you hit an issue when trying to install the agent.
A notification has been sent to Datadog with the following informations and the content of ddagent-install.log:
OS: $OS
Version: $agent_version
apikey: $key_to_report


You can send an email to help@datadoghq.com if you need support
and we'll do our very best to help you solve your problem\n\033[0m"

    curl -f -s -d "version=$agent_version&os=$OS&apikey=$key_to_report&log=$encoded_log" $dogweb_reporting_failure_url && echo -e "$notification_message"
}

function on_error() {
    set +e
    get_api_key_to_report
    get_os
    get_agent_version
    report_to_dogweb
    exit 1

}

function get_agent_version() {
    set +e
    agent_version=$(cd $HOME/.datadog-agent/agent && python -c "from config import get_version; print get_version()" || echo "Not determined")
    echo "version:$agent_version'"
    set -e
}


trap on_error ERR

if [ -n "$DD_API_KEY" ]; then
    apikey=$DD_API_KEY
fi

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

# set up the agent
mkdir -p $dd_base/agent
$dl_cmd $dd_base/agent.tar.gz https://github.com/DataDog/dd-agent/tarball/pup-release
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

if [ $OS = "MacOS" ]; then
    # prepare launchd
    mkdir -p $dd_base/launchd/logs
    touch $dd_base/launchd/logs/launchd.log
    sed "s|AGENT_BASE|$dd_base|; s|USER_NAME|$(whoami)|" $dd_base/agent/packaging/datadog-agent/osx/com.datadoghq.Agent.plist.example > $dd_base/launchd/com.datadoghq.Agent.plist
fi

# consolidate logging
mkdir -p $dd_base/logs
ln -s $dd_base/supervisord/logs $dd_base/logs/supervisord
if [ $OS = "MacOS" ]; then
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
    echo -e "\033[32m
Your agent has started up for the first time. We're currently
verifying that data is being submitted. You should see your agent show
up in Datadog within a few seconds at:

    https://app.datadoghq.com/account/settings#agent\033[0m

Waiting for metrics...\c"

    c=0
    while [ "$c" -lt "30" ]; do
        sleep 1
        echo -e ".\c"
        c=$(($c+1))
    done

    curl -f http://localhost:17123/status?threshold=0 > /dev/null 2>&1
    success=$?
    while [ "$success" -gt "0" ]; do
        sleep 1
        echo -e ".\c"
        curl -f http://localhost:17123/status?threshold=0 > /dev/null 2>&1
        success=$?
    done

    # Report installation success to dogweb for stats purpose
    set +e
    get_os
    echo "Trying to get agent_version"
    get_agent_version
    echo "Reporting installation success to dogweb"
    
    curl -d "version=$agent_version&os=$OS" $dogweb_reporting_success_url > /dev/null 2>&1
    # print instructions
    echo -e "\033[32m

Success! Your agent is functioning properly, and will continue to run
in the foreground. To stop it, simply press CTRL-C. To start it back
up again in the foreground, run:

cd $dd_base
sh bin/agent
"

    if [ $OS = "MacOS" ]; then
    echo "To set it up as a daemon that always runs in the background
while you're logged in, run:

    mkdir -p ~/Library/LaunchAgents
    cp $dd_base/launchd/com.datadoghq.Agent.plist ~/Library/LaunchAgents/.
    launchctl load -w ~/Library/LaunchAgents/com.datadoghq.Agent.plist
"
    fi

    echo -e "\033[0m\c"

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

    if [ $OS = "MacOS" ]; then
    echo -e "To set it up as a daemon that always runs in the background
while you're logged in, run:

    mkdir -p ~/Library/LaunchAgents
    cp $dd_base/launchd/com.datadoghq.Agent.plist ~/Library/LaunchAgents/.
    launchctl load -w ~/Library/LaunchAgents/com.datadoghq.Agent.plist
"
    fi

    echo "\033[0m\c"
fi

wait $agent_pid