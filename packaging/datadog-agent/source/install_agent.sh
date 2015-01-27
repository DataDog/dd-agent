#!/bin/bash
# Datadog Agent install script.
set -e
logfile="ddagent-install.log"
gist_request=/tmp/agent-gist-request.tmp
gist_response=/tmp/agent-gist-response.tmp

if [ $(which curl) ]; then
    dl_cmd="curl -f"
else
    dl_cmd="wget --quiet"
fi

# Set up a named pipe for logging
npipe=/tmp/$$.tmp
mknod $npipe p

# Log all output to a log for error checking
tee <$npipe $logfile &
exec 1>&-
exec 1>$npipe 2>&1
trap "rm -f $npipe" EXIT


function on_error() {
    printf "\033[31m$ERROR_MESSAGE
It looks like you hit an issue when trying to install the Agent.

Troubleshooting and basic usage information for the Agent are available at:

    http://docs.datadoghq.com/guides/basic_agent_usage/

If you're still having problems, please send an email to support@datadoghq.com
with the contents of ddagent-install.log and we'll do our very best to help you
solve your problem.\n\033[0m\n"
}
trap on_error ERR

if [ -n "$DD_API_KEY" ]; then
    apikey=$DD_API_KEY
fi

if [ ! $apikey ]; then
    printf "\033[31mAPI key not available in DD_API_KEY environment variable.\033[0m\n"
    exit 1;
fi

# OS/Distro Detection
# Try lsb_release, fallback with /etc/issue then uname command
KNOWN_DISTRIBUTION="(Debian|Ubuntu|RedHat|CentOS|openSUSE|Amazon)"
DISTRIBUTION=$(lsb_release -d 2>/dev/null | grep -Eo $KNOWN_DISTRIBUTION  || grep -Eo $KNOWN_DISTRIBUTION /etc/issue 2>/dev/null || uname -s)

if [ $DISTRIBUTION = "Darwin" ]; then
    printf "\033[31mThis script does not support installing on the Mac.

Please use the 1-step script available at https://app.datadoghq.com/account/settings#agent/mac.\033[0m\n"
    exit 1;

elif [ -f /etc/debian_version -o "$DISTRIBUTION" == "Debian" -o "$DISTRIBUTION" == "Ubuntu" ]; then
    OS="Debian"
elif [ -f /etc/redhat-release -o "$DISTRIBUTION" == "RedHat" -o "$DISTRIBUTION" == "CentOS" -o "$DISTRIBUTION" == "openSUSE" -o "$DISTRIBUTION" == "Amazon" ]; then
    OS="RedHat"
# Some newer distros like Amazon may not have a redhat-release file
elif [ -f /etc/system-release -o "$DISTRIBUTION" == "Amazon" ]; then
    OS="RedHat"
fi

# Root user detection
if [ $(echo "$UID") = "0" ]; then
    sudo_cmd=''
else
    sudo_cmd='sudo'
fi

DDBASE=false
# Python Detection
has_python=$(which python || echo "no")
if [ "$has_python" != "no" ]; then
    PY_VERSION=$(python -c 'import sys; print "%d.%d" % (sys.version_info[0], sys.version_info[1])')
    if [ $PY_VERSION = "2.4" -o $PY_VERSION = "2.5" ]; then
        DDBASE=true
    fi
fi

# Install the necessary package sources
if [ $OS = "RedHat" ]; then
    echo -e "\033[34m\n* Installing YUM sources for Datadog\n\033[0m"

    UNAME_M=$(uname -m)
    if [ "$UNAME_M"  == "i686" -o "$UNAME_M"  == "i386" -o "$UNAME_M"  == "x86" ]; then
        ARCHI="i386"
    else
        ARCHI="x86_64"
    fi
    $sudo_cmd sh -c "echo -e '[datadog]\nname = Datadog, Inc.\nbaseurl = http://yum.datadoghq.com/rpm/$ARCHI/\nenabled=1\ngpgcheck=0\npriority=1' > /etc/yum.repos.d/datadog.repo"

    printf "\033[34m* Installing the Datadog Agent package\n\033[0m\n"

    if $DDBASE; then
        DD_BASE_INSTALLED=$(yum list installed datadog-agent-base > /dev/null 2>&1 || echo "no")
        if [ "$DD_BASE_INSTALLED" != "no" ]; then
            echo -e "\033[34m\n* Uninstall datadog-agent-base\n\033[0m"
            $sudo_cmd yum -y remove datadog-agent-base
        fi
    fi
    $sudo_cmd yum -y install datadog-agent
elif [ $OS = "Debian" ]; then
    printf "\033[34m\n* Installing APT package sources for Datadog\n\033[0m\n"
    $sudo_cmd sh -c "echo 'deb http://apt.datadoghq.com/ stable main' > /etc/apt/sources.list.d/datadog.list"
    $sudo_cmd apt-key adv --recv-keys --keyserver hkp://keyserver.ubuntu.com:80 C7A7DA52

    printf "\033[34m\n* Installing the Datadog Agent package\n\033[0m\n"
    ERROR_MESSAGE="ERROR
Failed to update the sources after adding the Datadog repository.
This may be due to any of the configured APT sources failing -
see the logs above to determine the cause.
If the failing repository is Datadog, please contact Datadog support.
*****
"
    $sudo_cmd apt-get update
    ERROR_MESSAGE="ERROR
Failed to install the Datadog package, sometimes it may be
due to another APT source failing. See the logs above to
determine the cause.
If the cause is unclear, please contact Datadog support.
*****
"
    $sudo_cmd apt-get install -y --force-yes datadog-agent
    ERROR_MESSAGE=""
else
    printf "\033[31mYour OS or distribution are not supported by this install script.
Please follow the instructions on the Agent setup page:

    https://app.datadoghq.com/account/settings#agent\033[0m\n"
    exit;
fi

# Set the configuration
if [ -e /etc/dd-agent/datadog.conf ]; then
    printf "\033[34m\n* Keeping old datadog.conf configuration file\n\033[0m\n"
else
    printf "\033[34m\n* Adding your API key to the Agent configuration: /etc/dd-agent/datadog.conf\n\033[0m\n"
    $sudo_cmd sh -c "sed 's/api_key:.*/api_key: $apikey/' /etc/dd-agent/datadog.conf.example > /etc/dd-agent/datadog.conf"
fi

printf "\033[34m* Starting the Agent...\n\033[0m\n"
$sudo_cmd /etc/init.d/datadog-agent restart

# Wait for metrics to be submitted by the forwarder
printf "\033[32m
Your Agent has started up for the first time. We're currently verifying that
data is being submitted. You should see your Agent show up in Datadog shortly
at:

    https://app.datadoghq.com/infrastructure\033[0m

Waiting for metrics..."

c=0
while [ "$c" -lt "30" ]; do
    sleep 1
    echo -n "."
    c=$(($c+1))
done

$dl_cmd http://127.0.0.1:17123/status?threshold=0 > /dev/null 2>&1
success=$?
while [ "$success" -gt "0" ]; do
    sleep 1
    echo -n "."
    $dl_cmd http://127.0.0.1:17123/status?threshold=0 > /dev/null 2>&1
    success=$?
done

# Metrics are submitted, echo some instructions and exit
printf "\033[32m

Your Agent is running and functioning properly. It will continue to run in the
background and submit metrics to Datadog.

If you ever want to stop the Agent, run:

    sudo /etc/init.d/datadog-agent stop

And to run it again run:

    sudo /etc/init.d/datadog-agent start

\033[0m"
