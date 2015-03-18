#!/bin/sh

# figure out where to pull from
tag="5.2.1"

PIP_VERSION="6.0.6"

#######################
# Define some helpers #
#######################

dogweb_reporting_failure_url="https://app.datadoghq.com/agent_stats/report_failure"
email_reporting_failure="support@datadoghq.com"
agent_help_page="http://docs.datadoghq.com/guides/basic_agent_usage/"
see_agent_on_datadog_page="https://app.datadoghq.com/infrastructure"

RED="\033[31m"
GREEN="\033[32m"
DEFAULT="\033[0m"

# Function to display a message passed as an argument in red and then exit
quit_error() {
  printf "$RED"
  printf "$1" | tee -a $logfile
  printf "\nExiting...\n" | tee -a $logfile
  printf "$DEFAULT"
  exit 1
}

get_api_key_to_report() {
    if [ $apikey ]; then
        key_to_report=$apikey
    else
        key_to_report="No_key"
    fi
}

# Try to use curl to post the log in case of failure to an endpoint
# Will try to send it by mail usint the mail function if curl failed
report() {
    get_api_key_to_report
    log=$(cat "$logfile")
    encoded_log=$(echo "$log" | python -c 'import sys, urllib; print urllib.quote(sys.stdin.read().strip())')
    OS=$(echo "$unamestr" | python -c 'import sys, urllib; print urllib.quote(sys.stdin.read().strip())')
    key_to_report=$(echo "$key_to_report" | python -c 'import sys, urllib; print urllib.quote(sys.stdin.read().strip())')
    agent_version=$(echo "$tag" | python -c 'import sys, urllib; print urllib.quote(sys.stdin.read().strip())')
    notification_message="$RED
A notification has been sent to Datadog with the content of $logfile.

Troubleshooting and basic usage information for the Agent are available at:

    $agent_help_page

If you're still having problems please send an email to $email_reporting_failure
and we'll do our very best to help you solve your problem.\n$DEFAULT"

    curl -f -s -d "version=$agent_version&os=$OS&apikey=$key_to_report&log=$encoded_log" $dogweb_reporting_failure_url >> $logfile 2>&1 && printf "$notification_message" || report_using_mail

    exit 1

}

# If the user doesn't want to automatically report, display a message so he can reports manually
report_manual() {

   printf "$RED
Troubleshooting and basic usage information for the Agent are available at:

    $agent_help_page

If you're still having problems, please send an email to $email_reporting_failure
with the content of $logfile and any
information you think would be useful and we'll do our very best to help you
solve your problem.

\n$DEFAULT"

 exit 1

}

# Try to send the report using the mail function if curl failed, and display
# a message in case the mail function also failed
report_using_mail() {
    log=$(cat "$logfile")
    notfication_message_manual="$RED
Unable to send the report (you need curl or mail to send the report).

Troubleshooting and basic usage information for the Agent are available at:

    $agent_help_page

If you're still having problems, please send an email to $email_reporting_failure
with the content of $logfile and any
information you think would be useful and we'll do our very best to help you
solve your problem.


\n$DEFAULT"

    printf "$log" | mail -s "Agent source installation failure" $email_reporting_failure  2>> $logfile && printf "$notification_message" | tee -a $logfile || printf "$notfication_message_manual" | tee -a $logfile

exit 1

}

# Will be called if an unknown error appears and that the Agent is not running
# It asks the user if he wants to automatically send a failure report
unknown_error() {
  printf "$RED It looks like you hit an issue when trying to install the Agent.\n$DEFAULT" | tee -a $logfile
  printf "$1" | tee -a $logfile

  while true; do
    read -p "Do you want to send a failure report to Datadog (Content of the report is in $logfile)? (y/n)" yn
    case $yn in
        [Yy]* ) report; break;;
        [Nn]* ) report_manual; break;;
        * ) echo "Please answer yes or no.";;
    esac
  done
}


# Small helper to display "Done"
print_done() {
  printf "$GREEN"
  printf "Done\n" | tee -a $logfile
  printf "$DEFAULT"
}

unamestr=`uname`


#################################
# Beginning of the installation #
#################################

printf "\n\nInstalling Datadog Agent $tag\n\n\n"


if [ -n "$DD_API_KEY" ]; then
    apikey=$DD_API_KEY
fi

if [ -n "$DD_HOME" ]; then
    dd_home=$DD_HOME
fi

if [ -n "$DD_START_AGENT" ]; then
    start_agent=$DD_START_AGENT
else
    start_agent=1
fi

if [ -n "$IS_OPENSHIFT" ]; then
    is_openshift=$IS_OPENSHIFT
else
    is_openshift=0
fi


# Checking sysstat is installed
if [ "$unamestr" != "Darwin" ]; then
  iostat > /dev/null 2>&1
  success=$?
  if [ $success != 0 ]; then
    quit_error "sysstat is not installed in your system
If you run CentOs/RHEL, you can install it by running:
  sudo yum install sysstat
If you run Debian/Ubuntu, you can install it by running:
  sudo apt-get install sysstat"
  fi
fi

# Check python >= 2.6 is installed
python -c "import sys; exit_code = 0 if sys.version_info[0]==2 and sys.version_info[1] > 5 else 66 ; sys.exit(exit_code)" > /dev/null 2>&1
success=$?
if [ $success != 0 ]; then
  quit_error "Python 2.6 or 2.7 is required to install the Agent from source."
fi

# Determining which command to use to download files
if [ $(which curl) ]; then
    dl_cmd="curl -k -L -o"
else
    dl_cmd="wget -O"
fi

# create home base for the Agent
if [ $dd_home ]; then
  dd_base=$dd_home
else
  if [ "$unamestr" = "SunOS" ]; then
      dd_base="/opt/local/datadog"
  else
      dd_base=$HOME/.datadog-agent
  fi
fi


printf "Creating Agent directory $dd_base....."
mkdir -p $dd_base
printf "$GREEN Done\n$DEFAULT"

logfile="$dd_base/ddagent-install.log"
printf "Creating log file $logfile....." | tee -a $logfile
print_done

# Log the operating system version
printf "Operating System: $unamestr\n" >> $logfile

# set up a virtual env
printf "Setting up virtual environment....." | tee -a $logfile
$dl_cmd $dd_base/virtualenv.py https://raw.githubusercontent.com/pypa/virtualenv/1.11.6/virtualenv.py >> $logfile 2>&1

if [ "$is_openshift" = "1" ]; then
    python $dd_base/virtualenv.py --no-pip --no-setuptools --system-site-packages $dd_base/venv >> $logfile 2>&1
else
    python $dd_base/virtualenv.py --no-pip --no-setuptools $dd_base/venv >> $logfile 2>&1
fi

. $dd_base/venv/bin/activate >> $logfile 2>&1
print_done

# set up setuptools and pip with wheels support
printf "Setting up setuptools and pip....." | tee -a $logfile
$dl_cmd $dd_base/ez_setup.py https://bitbucket.org/pypa/setuptools/raw/bootstrap/ez_setup.py >> $logfile 2>&1
$dd_base/venv/bin/python $dd_base/ez_setup.py >> $logfile 2>&1
$dl_cmd $dd_base/get-pip.py https://raw.github.com/pypa/pip/master/contrib/get-pip.py >> $logfile 2>&1
$dd_base/venv/bin/python $dd_base/get-pip.py >> $logfile 2>&1
$dd_base/venv/bin/pip install pip==$PIP_VERSION >> $logfile 2>&1
print_done

# install dependencies
printf "Installing requirements using pip....." | tee -a $logfile
$dl_cmd $dd_base/requirements.txt https://raw.githubusercontent.com/DataDog/dd-agent/$tag/source-requirements.txt  >> $logfile 2>&1
$dd_base/venv/bin/pip install -r $dd_base/requirements.txt >> $logfile 2>&1
rm $dd_base/requirements.txt
print_done

printf "Trying to install optional dependencies using pip....." | tee -a $logfile
$dl_cmd $dd_base/requirements.txt https://raw.githubusercontent.com/DataDog/dd-agent/$tag/source-optional-requirements.txt  >> $logfile 2>&1
while read DEPENDENCY
do
    ($dd_base/venv/bin/pip install $DEPENDENCY || printf "Cannot install $DEPENDENCY. There is probably no Compiler on the system.") >> $logfile 2>&1
done < $dd_base/requirements.txt
rm $dd_base/requirements.txt
print_done

# set up the Agent
mkdir -p $dd_base/agent >> $logfile 2>&1

printf "Downloading the latest version of the Agent from github (~2.5 MB)....." | tee -a $logfile
$dl_cmd $dd_base/agent.tar.gz https://github.com/DataDog/dd-agent/tarball/$tag >> $logfile 2>&1
print_done
printf "Uncompressing the archive....." | tee -a $logfile
tar -xz -C $dd_base/agent --strip-components 1 -f $dd_base/agent.tar.gz >> $logfile 2>&1
print_done

printf "Configuring datadog.conf file......" | tee -a $logfile
if [ $apikey ]; then
    sed "s/api_key:.*/api_key: $apikey/" $dd_base/agent/datadog.conf.example > $dd_base/agent/datadog.conf 2>> $logfile
else
  printf "No api key set. Assuming there is already a configuration file present." | tee -a $logfile
fi

if [ "$unamestr" = "SunOS" ]; then
    # disable syslog by default on SunOS as it causes errors
    sed -i "s/# log_to_syslog: yes/log_to_syslog: no/" $dd_base/agent/datadog.conf 2>> $logfile
fi
printf "disable_file_logging: True" >> $dd_base/agent/datadog.conf

print_done

printf "Setting up launching scripts....." | tee -a $logfile
mkdir -p $dd_base/bin >> $logfile 2>&1
cp $dd_base/agent/packaging/datadog-agent/source/agent $dd_base/bin/agent >> $logfile 2>&1
cp $dd_base/agent/packaging/datadog-agent/source/info  $dd_base/bin/info >> $logfile 2>&1
chmod +x $dd_base/bin/agent >> $logfile 2>&1
chmod +x $dd_base/bin/info >> $logfile 2>&1
print_done

# This is the script that will be used by SMF
if [ "$unamestr" = "SunOS" ]; then
    cp $dd_base/agent/packaging/datadog-agent/smartos/dd-agent $dd_base/bin/dd-agent >> $logfile 2>&1
    chmod +x $dd_base/bin/dd-agent >> $logfile 2>&1
fi

# set up supervisor
printf "Setting up supervisor....." | tee -a $logfile
mkdir -p $dd_base/supervisord/logs >> $logfile 2>&1
$dd_base/venv/bin/pip install supervisor==3.0b2 >> $logfile 2>&1
cp $dd_base/agent/packaging/datadog-agent/source/supervisord.conf $dd_base/supervisord/supervisord.conf >> $logfile 2>&1
print_done

if [ "$unamestr" = "Darwin" ]; then
    # prepare launchd
    mkdir -p $dd_base/launchd/logs >> $logfile 2>&1
    touch $dd_base/launchd/logs/launchd.log >> $logfile 2>&1
    sed "s|AGENT_BASE|$dd_base|; s|USER_NAME|$(whoami)|" $dd_base/agent/packaging/datadog-agent/osx/com.datadoghq.Agent.plist.example > $dd_base/launchd/com.datadoghq.Agent.plist
fi

# consolidate logging
printf "Consolidating logging....." | tee -a $logfile
mkdir -p $dd_base/logs >> $logfile 2>&1
ln -s $dd_base/supervisord/logs $dd_base/logs/supervisord >> $logfile 2>&1
if [ "$unamestr" = "Darwin" ]; then
    ln -s $dd_base/launchd/logs $dd_base/logs/launchd >> $logfile 2>&1
fi
print_done

# clean up
printf "Cleaning up the installation directory....." | tee -a $logfile
rm $dd_base/virtualenv.py >> $logfile 2>&1
rm $dd_base/virtualenv.pyc >> $logfile 2>&1
rm $dd_base/agent.tar.gz >> $logfile 2>&1
print_done

# on solaris, skip the test, svcadm the Agent
if [ "$unamestr" = "SunOS" ]; then
    # Install pyexpat for our version of python, a dependency for xml parsing (varnish et al.)
    # Tested with /bin/sh
    python -V 2>&1 | awk '{split($2, arr, "."); printf("py%d%d-expat", arr[1], arr[2]);}' | xargs pkgin -y in
    # SMF work now
    svccfg import $dd_base/agent/packaging/datadog-agent/smartos/dd-agent.xml >> $logfile 2>&1
    svcadm enable site/datadog >> $logfile 2>&1
    svcs datadog >> $logfile 2>&1

    printf "*** The Agent is running. My work here is done... ( ^_^) ***" | tee -a $logfile
    printf "

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
    " | tee -a $logfile
    # kthxbye
    exit $?
else
  if [ "$start_agent" = "1" ]; then
      printf "Starting the Agent....." | tee -a $logfile
      # run Agent
      cd $dd_base >> $logfile 2>&1
      supervisord -c $dd_base/supervisord/supervisord.conf >> $logfile 2>&1 &
      agent_pid=$!
      sleep 1
      # Checking that supervisord was properly launched
      kill -0 $agent_pid > /dev/null 2>&1
      supervisor_running=$?

      if [ $supervisor_running != 0 ]; then
        unknown_error "Failure when launching supervisor.\n"

      fi
      trap "{ kill $agent_pid; exit 255; }" INT TERM
      trap "{ kill $agent_pid; exit; }" EXIT
      print_done


      # wait for metrics to be submitted
      printf "$GREEN
  Your Agent has started up for the first time. We're currently verifying
  that data is being submitted. You should see your Agent show up in Datadog
  shortly at:

      $see_agent_on_datadog_page $DEFAULT" | tee -a $logfile

    printf "\n\nWaiting for metrics..." | tee -a $logfile

      c=0
      # Wait for 30 secs before checking if metrics have been submitted
      while [ "$c" -lt "30" ]; do
          sleep 1
          printf "."
          c=$(($c+1))
      done

      # Hit this endpoint to check if the Agent is submitting metrics
      # and retry every sec for 60 more sec before failing
      curl -f http://localhost:17123/status?threshold=0 >> $logfile 2>&1
      success=$?
      while [ "$success" -gt "0" ]; do
          sleep 1
          printf "."
          curl -f http://localhost:17123/status?threshold=0 >> $logfile 2>&1
          success=$?
          c=$(($c+1))
          if [ "$c" -gt "90" ]; then
            unknown_error "Agent did not submit metrics after 90 seconds
            "
          fi
      done

      # print instructions
      printf "$GREEN

  Success! Your Agent is functioning properly, and will continue to run
  in the foreground. To stop it, simply press CTRL-C. To start it back
  up again in the foreground, run:

  cd $dd_base
  sh bin/agent

  " | tee -a $logfile

      if [ "$unamestr" = "Darwin" ]; then
      echo "To set it up as a daemon that always runs in the background
  while you're logged in, run:

      mkdir -p ~/Library/LaunchAgents
      cp $dd_base/launchd/com.datadoghq.Agent.plist ~/Library/LaunchAgents/.
      launchctl load -w ~/Library/LaunchAgents/com.datadoghq.Agent.plist
  " | tee -a $logfile
      fi

      printf "$DEFAULT"

    wait $agent_pid
  fi
fi
