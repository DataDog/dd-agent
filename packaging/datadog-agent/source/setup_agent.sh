#!/bin/sh
# Bail on errors
set -e
# We shouldn't have unbounded vars
set -u

#######################################################################
# SCRIPT KNOBS
#######################################################################
# Update for new releases, will pull this tag in the repo
DEFAULT_AGENT_VERSION="5.6.3"
# Pin pip version, in the past there was some buggy releases and get-pip.py
# always pulls the latest version
PIP_VERSION="6.0.8"
VIRTUALENV_VERSION="1.11.6"
SUPERVISOR_VERSION="3.0b2"

#######################################################################
# OVERRIDABLE VARIABLES:
# $AGENT_VERSION
#   The tag or branch from which the source install performs.
#   Defaults to $DEFAULT_AGENT_VERSION
# $DD_API_KEY
#   Sets your API key in the config when installing.
#   If not specified, the script will not install a default config.
#   You can find a sample at $DD_HOME/datadog.conf.example and create
#   one yourself at $DD_HOME/datadog.conf
# $DD_HOME
#   Sets the agent installation directory.
#   Defaults to $HOME/.datadog-agent
# $DD_START_AGENT
#   0/1 value. 1 will start the agent at the end of the script
#   Defaults to 1.
# $DD_DOG
#   0/1 value. 1 will print a cute pup at the beginning of the script
#   Defaults to 0.
#
#
# $IS_OPENSHIFT DEPRECATED!
#   Used to be a different setup for OpenShift, it's no a noop, upgrade
#   your cartridge if you're using it.
#######################################################################
set +u # accept temporarily unbound vars, because we set defaults
AGENT_VERSION=${AGENT_VERSION:-$DEFAULT_AGENT_VERSION}

# If DD_HOME is unset
if [ -z "$DD_HOME" ]; then
    # Compatibilty: dd_home used in lieu of DD_HOME
    if [ -n "$dd_home" ]; then
        DD_HOME="$dd_home"
    else
        if [ "$(uname)" = "SunOS" ]; then
            DD_HOME="/opt/local/datadog"
        else
            DD_HOME=$HOME/.datadog-agent
        fi
    fi
fi

DD_API_KEY=${DD_API_KEY:-no_key}

DD_START_AGENT=${DD_START_AGENT:-1}

if [ -n "$IS_OPENSHIFT" ]; then
    printf "IS_OPENSHIFT is deprecated and won't do anything\n"
fi

DD_DOG=${DD_DOG:-0}
set -u
#######################################################################
# CONSTANTS
#######################################################################
REPORT_FAILURE_URL="https://app.datadoghq.com/agent_stats/report_failure"
REPORT_FAILURE_EMAIL="support@datadoghq.com"

AGENT_HELP_URL="http://docs.datadoghq.com/guides/basic_agent_usage/"
INFRA_URL="https://app.datadoghq.com/infrastructure"
DOG="

                                         7           77II?+~,,,,,,
                                        77II?~:,,,,,,,,,,,,,,,,,,,
                           77I?+~:,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,I
   7         77II?+~,,,,,,,,,,,,,,,,,,,,,,,,,,,,I :,,,,,,,,,,,,,,,:
  II?=:,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,:   ~  +,,,,,,,,,,,,,,
  ,,,,,,,,,,,,,,,,,=7:,,,,,,,,,,,,,,,,,,,,,,~    =   7,,,,,,,,,,,,,7
  ,,,,,,,,,,,,,=     =7,,,,,,,,,,, ~7:I,,,:      7I    ,,,,,,,,,,,,I
  ,,,,,,,,,,,,7       ,  ,,,,,=                   ,7    ,,,,,,,,,,,,
  I,,,,,,,,,,         +~                     7:I  ,,   7 ,,,,,,,,,,,
   ,,,,,,,,+           ,I                     7 ,+ ,,I   +,,,,,,,,,,7
   ,,,,,,,,            ,,                        ,,,,,,I7?,,,,,,,,,,+
   :,,,,,,,            7,                         ,,,,,,,,,,,,,,,,,,,
   7,,,,,,,7            ,7                         ,,,,,,,,,,,,,,,,,,
    ,,,,,,,,7           ,7                    7,,,I ,,,,,,,,,,,,,,,,,7
    ,,,,,,,,,I         7,7      7I:,,:         I,,,7:,,,,,,,,,,,,,,,,=
    =,,,,,,,,,,       I,,      7,,,,,  7        ?,, =,,,,,,,,,,,,,,,,,
    7,,,,,,,,,,,,I77?,,,       =,,,,,7              ?,,,,,,,,,,,,,,,,,
     ,,,,,,,,,,,,,,,,,          ,,,=                 7,,,,,,,,,,,,,,,,
     ,,,,,,,,,,,,=                                     ,,,,,,,,,,,,,,,7
     ,,,,,,,,,,,,:                                      ,,,,,,,,,,,,,,=
     ~,,,,,,,,,,,, 7                             I?~,,,7 ,,,,,,,,,,,,,,
     7,,,,,,,,,,,,I                            7,,,,,,,7 ,,,,,,,,,,,,,,
      ,,,,,,,,,,,,,  7                          ,,,,,,,7 ,,,,,,,,,,,,,,I
      ,,,,,,,,,,,,,7 7                            ~,,:   ,,,,,,,,,,,,,,:
      =,,,,,,,,,,,,:,7           I                 77   ?,,,,,,,,,,,,,,,
      7,,,,,,,,,,,,,,,          7 ,7              7,    ,,,,,,,,,,,,,:,,7 7
       ,,,,,,,,,,,,,,,,,           :,I           7,,+?~,,,,,:?       7,,I
       ,,,,,,,,,,,,,,,,,:            ,,,I      7+,,,=                 ,,,
       ?,,,,,,,,,,,,,,,,,        +:,,,,,,,,,,,,,,                     ,,,
        ,,,,,,,,,,,,,,,,,        7,7       ~,~   7                7,  ,,,77
        ,,,,,,,,,,,,,,,,,         ,=                     7       I,,7 ,,,+
        ,,,,,,,,,,,,,,,,I         ,,                    7       7,,,7 ,,,,
        I,,,,,,,,,,,,,,           ,,                   ,,,I    I,,,,+ ,,,,
         ,,,,,,,,,,,,7  7         +,                  ?,,,,,7 =,,,,,: ,,,,7
         ,,,,,,,,,,?+,,,,,,?      7,7               7?,,,,,,,,,,,,,,, =,,,=
         :,,,,,,,,,       7,,I     ,=        ~I     I,,,,,,,,,,,,,,,, 7,,,,
         7,,,,,,            ,,     ,,     7 ?,,,~7 I,,,,,,,,,,,,,,,,, 7,,,,
          ,,,,,              ,,    ,,     7+,,,,,,,,,,,,,,,,,,,,,,,,,7 ,,,,
          ,,,,                ,I   ,,     +,,,,,,,,,,,,,,,,,,,,,,,,,,I ,,,,7
          ,,,,7               ,,   =,7  7+,,,,,,,,,,,,,,,,,,,,,,,,,,,= ,,7
          :,,,:               I,III=,=  =,,,,,,,,,,,,,,,,,,,,,~7   7  7,,=
          7,,,,:              7,,,,,,,  ,,,,,,,,,,,,,,+       7I?~,,,,,,,,
           ,,,,,,              ,=7 7,,  ,,,,,=    7  7I?=,,,,,,,,,,,,,,,,,7
           ,,,,,,:            7,    ,,       II+:,,,,,,,,,,,,,,,,,,~?
                  7           :,    ,,?~,,,,,,,,,,,,,,:?
                              ,+    ,,,,,:=7
                    I       7,,
                    I,,~++:,,,
                       ?:,:I 7
"

LOGFILE="$DD_HOME/ddagent-install.log"
BASE_GITHUB_URL="https://raw.githubusercontent.com/DataDog/dd-agent/$AGENT_VERSION"

#######################################################################
# Error reporting helpers
#######################################################################
print_console() {
    printf "%s\n" "$*" | tee /dev/fd/3
}

print_console_wo_nl() {
    printf "%s" "$*" | tee /dev/fd/3
}

print_red() {
    printf "\033[31m%s\033[0m\n" "$*" | tee /dev/fd/3
}

print_green() {
    printf "\033[32m%s\033[0m\n" "$*" | tee /dev/fd/3
}

print_done() {
    print_green "Done"
}

# If the user doesn't want to automatically report, give info so he can report manually
report_manual() {
    print_red "Troubleshooting and basic usage information for the Agent are available at:

    $AGENT_HELP_URL

If you're still having problems, please send an email to $REPORT_FAILURE_EMAIL
with the content of $LOGFILE and any
information you think would be useful and we'll do our very best to help you
solve your problem."
    exit 1
}

# Try to send the report using the mail function if curl failed, and display
# a message in case the mail function also failed
report_using_mail() {
    if mail -s "Agent source installation failure" "$REPORT_FAILURE_EMAIL" < "$LOGFILE"; then
        print_red "Unable to send the report (you need curl or mail to send the report).

Troubleshooting and basic usage information for the Agent are available at:

    $REPORT_FAILURE_URL

If you're still having problems, please send an email to $REPORT_FAILURE_EMAIL
with the content of $LOGFILE and any
information you think would be useful and we'll do our very best to help you
solve your problem."
        exit 1
    else
        report_manual
    fi
}

# Try to use curl to post the log in case of failure to an endpoint
# Will try to send it by mail using the mail function if curl failed
report() {
    ESC_LOG=$(python -c 'import sys, urllib; print urllib.quote(sys.stdin.read().strip())' < "$LOGFILE")
    ESC_OS=$(uname | python -c 'import sys, urllib; print urllib.quote(sys.stdin.read().strip())')
    ESC_API_KEY=$(echo "$DD_API_KEY" | python -c 'import sys, urllib; print urllib.quote(sys.stdin.read().strip())')
    ESC_AGENT_VERSION=$(echo "$AGENT_VERSION" | python -c 'import sys, urllib; print urllib.quote(sys.stdin.read().strip())')

    if curl -f -s -d "version=$ESC_AGENT_VERSION&os=$ESC_OS&apikey=$ESC_API_KEY&log=$ESC_LOG" $REPORT_FAILURE_URL; then
        print_red "A notification has been sent to Datadog with the content of $LOGFILE

Troubleshooting and basic usage information for the Agent are available at:

    $AGENT_HELP_URL

If you're still having problems please send an email to $REPORT_FAILURE_EMAIL
and we'll do our very best to help you solve your problem."
        exit 1
    else
        report_using_mail
    fi
}

# Will be called if an unknown error appears and that the Agent is not running
# It asks the user if he wants to automatically send a failure report
error_trap() {
    print_red "It looks like you hit an issue when trying to install the Datadog agent."
    print_console "###"
    if [ -n "$ERROR_MESSAGE" ]; then
        print_red "$ERROR_MESSAGE"
    else
        tail -n 5 "$LOGFILE" | tee /dev/fd/3
    fi
    print_console "###"

    print_console
    while true; do
        print_console "Do you want to send a failure report to Datadog (Content of the report is in $LOGFILE)? (y/n)"
        read yn
        case $yn in
            [Yy]* ) report; break;;
            [Nn]* ) report_manual; break;;
            * ) print_console "Please answer yes or no.";;
        esac
    done
}

#######################################################################
# PREPARING FOR EXECUTION
#######################################################################

# We need to create this dir beforehand to put the logfile somewhere
mkdir -p "$DD_HOME"
# Redirect all stdout/stderr to a log file
# Let fd 3 opened to output to console
exec 3>&1 1>>"$LOGFILE" 2>&1
# Check logfile is writable
print_console "Checking that logfile is writable"
print_green "OK"

# Catch errors and handle them
trap error_trap INT TERM EXIT

if [ "$DD_DOG" != "0" ]; then
    echo "$DOG" 1>&3
fi

#######################################################################
# CHECKING REQUIREMENTS
#######################################################################
detect_python() {
    if command -v python2.7; then
        export PYTHON_CMD="python2.7"
    elif command -v python2; then
        # FreeBSD apparently uses this
        export PYTHON_CMD="python2"
    else
        export PYTHON_CMD="python"
    fi
}

detect_downloader() {
    if command -v curl; then
        export DOWNLOADER="curl -k -L -o"
        export HTTP_TESTER="curl -f"
    elif command -v wget; then
        export DOWNLOADER="wget -O"
        export HTTP_TESTER="wget -O /dev/null"
    fi
}

detect_sed() {
    if command -v sed; then
        export SED_CMD="sed"
    fi
}

print_console "Checking installation requirements"

print_green "* uname $(uname)"

# Sysstat must be installed, except on Macs
ERROR_MESSAGE="sysstat is not installed on your system
If you run CentOs/RHEL, you can install it by running:
  sudo yum install sysstat
If you run Debian/Ubuntu, you can install it by running:
  sudo apt-get install sysstat"

if [ "$(uname)" != "Darwin" ]; then
    iostat > /dev/null 2>&1
fi
print_green "* sysstat is installed"

# Detect Python version
ERROR_MESSAGE="Python 2.6 or 2.7 is required to install the agent from source"
detect_python
if [ -z "$PYTHON_CMD" ]; then exit 1; fi
$PYTHON_CMD -c "import sys; exit_code = 0 if sys.version_info[0]==2 and sys.version_info[1] > 5 else 66 ; sys.exit(exit_code)" > /dev/null 2>&1
print_green "* python found, using \`$PYTHON_CMD\`"

# Detect downloader
ERROR_MESSAGE="curl OR wget are required to install the agent from source"
detect_downloader
if [ -z "$DOWNLOADER" ]; then exit 1; fi
print_green "* downloader found, using \`$DOWNLOADER\`"

# sed is required to "template" the configuration files
detect_sed
if [ -z "$SED_CMD" ]; then
    print_red "* sed command not found. Will proceed without configuring the agent"
else
    print_green "* sed found, using \`$SED_CMD\`"
fi


#######################################################################
# INSTALLING
#######################################################################

print_console
print_console
print_console "Installing Datadog Agent $AGENT_VERSION"
print_console "Installation is logged at $LOGFILE"
print_console

# The steps are detailed enough to know where it fails
ERROR_MESSAGE=""

print_console "* Setting up a python virtual env"
$DOWNLOADER "$DD_HOME/virtualenv.py" "https://raw.githubusercontent.com/pypa/virtualenv/$VIRTUALENV_VERSION/virtualenv.py"
$PYTHON_CMD "$DD_HOME/virtualenv.py" --no-pip --no-setuptools "$DD_HOME/venv"
rm -f "$DD_HOME/virtualenv.py"
rm -f "$DD_HOME/virtualenv.pyc"
print_done

print_console "* Activating the virtual env"
# venv activation script doesn't handle -u mode
set +u
. "$DD_HOME/venv/bin/activate"
set -u
print_done

VENV_PYTHON_CMD="$DD_HOME/venv/bin/python"
VENV_PIP_CMD="$DD_HOME/venv/bin/pip"

print_console "* Setting up setuptools"
$DOWNLOADER "$DD_HOME/ez_setup.py" https://bitbucket.org/pypa/setuptools/raw/bootstrap/ez_setup.py
$VENV_PYTHON_CMD "$DD_HOME/ez_setup.py"
rm -f "$DD_HOME/ez_setup.py"
rm -f "$DD_HOME/ez_setup.pyc"
print_done

print_console "* Setting up pip"
$DOWNLOADER "$DD_HOME/get-pip.py" https://bootstrap.pypa.io/get-pip.py
$VENV_PYTHON_CMD "$DD_HOME/get-pip.py"
$VENV_PIP_CMD install "pip==$PIP_VERSION"
rm -f "$DD_HOME/get-pip.py"
rm -f "$DD_HOME/get-pip.pyc"
print_done

print_console "* Installing requirements"
$DOWNLOADER "$DD_HOME/requirements.txt" "$BASE_GITHUB_URL/requirements.txt"
$VENV_PIP_CMD install -r "$DD_HOME/requirements.txt"
rm -f "$DD_HOME/requirements.txt"
print_done

print_console "* Downloading agent version $AGENT_VERSION from GitHub (~5 MB)"
mkdir -p "$DD_HOME/agent"
$DOWNLOADER "$DD_HOME/agent.tar.gz" "https://github.com/DataDog/dd-agent/tarball/$AGENT_VERSION"
print_done

print_console "* Uncompressing tarball"
tar -xz -C "$DD_HOME/agent" --strip-components 1 -f "$DD_HOME/agent.tar.gz"
rm -f "$DD_HOME/agent.tar.gz"
print_done

print_console "* Trying to install optional requirements"
$DOWNLOADER "$DD_HOME/requirements-opt.txt" "$BASE_GITHUB_URL/requirements-opt.txt"
"$DD_HOME/agent/utils/pip-allow-failures.sh" "$DD_HOME/requirements-opt.txt"
print_done

print_console "* Setting up a datadog.conf generic configuration file"
if [ "$DD_API_KEY" = "no_key" ]; then
    print_console "    Got no API KEY through $DD_API_KEY. Proceeding without installing datadog.conf"
elif [ -z "$SED_CMD" ]; then
    print_console "    No sed command. Proceeding without installing datadog.conf"
else
    # Install API key
    $SED_CMD "s/api_key:.*/api_key: $DD_API_KEY/" "$DD_HOME/agent/datadog.conf.example" > "$DD_HOME/agent/datadog.conf"
    # Disable syslog by default on SunOS as it causes errors
    if [ "$(uname)" = "SunOS" ]; then
        $SED_CMD -i "s/# log_to_syslog: yes/log_to_syslog: no/" "$DD_HOME/agent/datadog.conf"
    fi
    # Setting up logging
    # Needed to avoid "unknown var $prog_log_file"
    log_suffix="_log_file"
    for prog in collector forwarder dogstatsd jmxfetch; do
      echo "$prog$log_suffix: $DD_HOME/logs/$prog.log" >> "$DD_HOME/agent/datadog.conf"
    done
    chmod 640 "$DD_HOME/agent/datadog.conf"
fi
print_done

print_console "* Setting up init scripts"
mkdir -p "$DD_HOME/bin"
cp "$DD_HOME/agent/packaging/datadog-agent/source/agent" "$DD_HOME/bin/agent"
chmod +x "$DD_HOME/bin/agent"
if [ "$(uname)" = "SunOS" ]; then
    cp "$DD_HOME/agent/packaging/datadog-agent/smartos/dd-agent" "$DD_HOME/bin/dd-agent"
    chmod +x "$DD_HOME/bin/dd-agent"
fi
print_done

print_console "* Setting up supervisord"
mkdir -p "$DD_HOME/logs"
$VENV_PIP_CMD install "supervisor==$SUPERVISOR_VERSION"
cp "$DD_HOME/agent/packaging/datadog-agent/source/supervisor.conf" "$DD_HOME/agent/supervisor.conf"
mkdir -p "$DD_HOME/run"
print_done

print_console "* Starting the agent"
if [ "$DD_START_AGENT" = "0" ]; then
    print_console "    Skipping due to \$DD_AGENT_START"
    exit 0
fi

# on solaris, skip the test, svcadm the Agent
if [ "$(uname)" = "SunOs" ]; then
    # Install pyexpat for our version of python, a dependency for xml parsing (varnish et al.)
    # Tested with /bin/sh
    $PYTHON_CMD -V 2>&1 | awk '{split($2, arr, "."); printf("py%d%d-expat", arr[1], arr[2]);}' | xargs pkgin -y in
    # SMF work now
    svccfg import "$DD_HOME/agent/packaging/datadog-agent/smartos/dd-agent.xml"
    svcadm enable site/datadog
    if svcs datadog; then
        print_done
        print_console "*** The Agent is running. My work here is done... (^_^) ***"
        exit 0
    else
        # KTHXBYE
        exit $?
    fi
fi

# supervisord.conf uses relative paths so need to chdir
cd "$DD_HOME"
supervisord -c agent/supervisor.conf &
cd -
AGENT_PID=$!
sleep 1

# Checking that the agent is up
if ! kill -0 $AGENT_PID; then
    ERROR_MESSAGE="Failure when launching supervisord"
    exit 1
fi
print_green "    - supervisord started"

# On errors and exit, quit properly
trap '{ kill $AGENT_PID; exit 255; }' INT TERM
trap '{ kill $AGENT_PID; exit; }' EXIT

print_console
print_green "Your Agent has started up for the first time. We're currently verifying
that data is being submitted. You should see your Agent show up in Datadog
shortly at:

      $INFRA_URL"

print_console
print_console "* Waiting 30s to see if the Agent submits metrics correctly"
c=0
while [ "$c" -lt "30" ]; do
    sleep 1
    print_console_wo_nl "."
    c=$((c+1))
done

# Hit this endpoint to check if the Agent is submitting metrics
# and retry every sec for 60 more sec before failing
print_console
print_console "* Testing if the Agent is submitting metrics"
ERROR_MESSAGE="The Agent hasn't submitted metrics after 90 seconds"
while [ "$c" -lt "90" ]; do
    sleep 1
    print_console_wo_nl "."
    if $HTTP_TESTER "http://localhost:17123/status?threshold=0"; then
        break
    fi
    c=$((c+1))
done
print_console

if [ "$c" -ge "90" ]; then
    error_trap
fi

# Yay IT WORKED!
print_green "Success! Your Agent is functioning properly, and will continue to run
in the foreground. To stop it, simply press CTRL-C. To start it back
up again in the foreground, run:

    $DD_HOME/bin/agent
"

if [ "$(uname)" = "Darwin" ]; then
    print_console "To set it up as a daemon that always runs in the background
while you're logged in, run:

    mkdir -p ~/Library/LaunchAgents
    cp $DD_HOME/launchd/com.datadoghq.Agent.plist ~/Library/LaunchAgents/
    launchctl load -w ~/Library/LaunchAgents/com.datadoghq.Agent.plist
"
fi

wait $AGENT_PID
