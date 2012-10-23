#!/bin/bash
# Datadog Agent install script.
set -e

dogweb_reporting_failure_url="https://app.datadoghq.com/agent_stats/report_failure"
dogweb_reporting_success_url="https://app.datadoghq.com/agent_stats/report_success"
email_reporting_failure="help@datadoghq.com"
logfile="ddagent-install.log"
gist_request=/tmp/agent-gist-request.tmp
gist_response=/tmp/agent-gist-response.tmp


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
    echo -e "\033[31mThis script does not support installing on the Mac.

Please use the 1-step script available at https://app.datadoghq.com/account/settings#agent/mac.\033[0m"
    exit 1;
fi

# Set up a named pipe for logging
npipe=/tmp/$$.tmp
mknod $npipe p

# Log all output to a log for error checking
tee <$npipe $logfile &
exec 1>&-
exec 1>$npipe 2>&1

function report_using_mail() {
    if [ $? = 22 ]; then
        log=$(cat "$logfile")
        notfication_message_manual="\033[31m
    It looks like you hit an issue when trying to install the agent.

    Please send an email to help@datadoghq.com with the following content, the content of the file ddagent-install.log and any informations you think would be useful
    and we'll do our very best to help you solve your problem.

    Agent installation failure:
    OS: $OS
    Version: $agent_version

    \n\033[0m"

        echo -e "Agent installation failure: \n OS: $OS \n Version: $agent_version \n \n\n Log:$log" | mail -s "Agent installation failure" $email_reporting_failure && echo -e "$notification_message" || echo -e "$notfication_message_manual"
        exit 1
    fi
    rm -f $npipe

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
You can send an email to help@datadoghq.com if you need support
and we'll do our very best to help you solve your problem\n\033[0m

A notification has been sent to Datadog with the following informations and the content of ddagent-install.log:
OS: $OS
Version: $agent_version"

    curl -f -s -d "version=$agent_version&os=$OS&apikey=$key_to_report&log=$encoded_log" $dogweb_reporting_failure_url && echo -e "$notification_message"
}

function get_agent_version() {
    set +e
    agent_version="Repository"
    set -e
}

function on_error() {
    set +e
    get_api_key_to_report
    get_os
    get_agent_version
    report_to_dogweb
    exit 1

}


trap on_error ERR

if [ -n "$DD_API_KEY" ]; then
    apikey=$DD_API_KEY
fi

if [ ! $apikey ]; then
    echo -e "\033[31mAPI key not available in DD_API_KEY environment variable.\033[0m"
    exit 1;
fi

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

# Python Detection
has_python=$(which python || echo "no")
if [ $has_python = "no" ]; then
    echo -e "\033[31mPython is required to install the Datadog Agent.\033[0m"
    exit 1;
fi

PY_VERSION=$(python -c 'import sys; print "%d.%d" % (sys.version_info[0], sys.version_info[1])')

if [ $PY_VERSION = "2.4" -o $PY_VERSION = "2.5" ]; then
    DDBASE=true
else
    DDBASE=false
fi

# Install the necessary package sources
if [ $OS = "RedHat" ]; then
    echo -e "\033[34m\n* Installing YUM sources for Datadog\n\033[0m"
    sudo sh -c "echo -e '[datadog]\nname = Datadog, Inc.\nbaseurl = http://yum.datadoghq.com/rpm/\nenabled=1\ngpgcheck=0' > /etc/yum.repos.d/datadog.repo"

    echo -e "\033[34m* Installing the Datadog Agent package\n\033[0m"
    sudo yum makecache

    if $DDBASE; then
        sudo yum -y install datadog-agent-base
    else
        sudo yum -y install datadog-agent
    fi
elif [ $OS = "Debian" -o $OS = "Ubuntu" ]; then
    echo -e "\033[34m\n* Installing APT package sources for Datadog\n\033[0m"
    sudo sh -c "echo 'deb http://apt.datadoghq.com/ unstable main' > /etc/apt/sources.list.d/datadog-source.list"
    sudo apt-key adv --recv-keys --keyserver hkp://keyserver.ubuntu.com:80 C7A7DA52

    echo -e "\033[34m\n* Installing the Datadog Agent package\n\033[0m"
    sudo apt-get update
    if $DDBASE; then
        sudo apt-get install -y --force-yes datadog-agent-base
    else
        sudo apt-get install -y --force-yes datadog-agent
    fi
else
    echo -e "\033[31mYour OS or distribution are not supported by this install script.
Please follow the instructions on the agent setup pa.ge:

    https://app.datadoghq.com/account/settings#agent\033[0m"
    exit;
fi

echo -e "\033[34m\n* Adding your API key to the agent configuration: /etc/dd-agent/datadog.conf\n\033[0m"

if $DDBASE; then
    sudo sh -c "sed 's/api_key:.*/api_key: $apikey/' /etc/dd-agent/datadog.conf.example | sed 's/# dogstatsd_target :.*/dogstatsd_target: https:\/\/app.datadoghq.com/' > /etc/dd-agent/datadog.conf"
else
    sudo sh -c "sed 's/api_key:.*/api_key: $apikey/' /etc/dd-agent/datadog.conf.example > /etc/dd-agent/datadog.conf"
fi

echo -e "\033[34m* Starting the agent...\n\033[0m"
sudo /etc/init.d/datadog-agent restart

# Datadog "base" installs don't have a forwarder, so we can't use the same
# check for the initial payload being sent.
if $DDBASE; then

# Report installation success to dogweb for stats purpose
set +e
get_os
echo "Trying to get agent_version"
get_agent_version
echo "Reporting installation success to dogweb"
curl -d "version=$agent_version&os=$OS" $dogweb_reporting_success_url > /dev/null 2>&1

echo -en "\033[32m
Your agent has started up for the first time and is submitting metrics to
Datadog. You should see your agent show up in Datadog within a few seconds at:

    https://app.datadoghq.com/account/settings#agent\033[0m

If you ever want to stop the agent, run:

    sudo /etc/init.d/datadog-agent stop

And to run it again run:

    sudo /etc/init.d/datadog-agent start
"
exit 1;
fi

# Wait for metrics to be submitted by the forwarder
echo -en "\033[32m
Your agent has started up for the first time. We're currently
verifying that data is being submitted. You should see your agent show
up in Datadog within a few seconds at:

    https://app.datadoghq.com/account/settings#agent\033[0m

Waiting for metrics..."

c=0
while [ "$c" -lt "30" ]; do
    sleep 1
    echo -n "."
    c=$(($c+1))
done

curl -f http://127.0.0.1:17123/status?threshold=0 > /dev/null 2>&1
success=$?
while [ "$success" -gt "0" ]; do
    sleep 1
    echo -n "."
    curl -f http://127.0.0.1:17123/status?threshold=0 > /dev/null 2>&1
    success=$?
done

# Report installation success to dogweb for stats purpose
set +e
get_os
echo "Trying to get agent_version"
get_agent_version
echo "Reporting installation success to dogweb"
OS=$(echo "$OS" | python -c 'import sys, urllib; print urllib.quote(sys.stdin.read().strip())')
agent_version=$(echo "$agent_version" | python -c 'import sys, urllib; print urllib.quote(sys.stdin.read().strip())')
curl -d "version=$agent_version&os=$OS" $dogweb_reporting_success_url > /dev/null 2>&1

# Metrics are submitted, echo some instructions and exit
echo -e "\033[32m

Your agent is running and functioning properly. It will continue to run in the
background and submit metrics to Datadog.

If you ever want to stop the agent, run:

    sudo /etc/init.d/datadog-agent stop

And to run it again run:

    sudo /etc/init.d/datadog-agent start

\033[0m"