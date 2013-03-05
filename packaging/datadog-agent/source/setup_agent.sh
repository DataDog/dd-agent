#!/bin/sh

if [ -n "$DD_API_KEY" ]; then
    apikey=$DD_API_KEY
fi

if [ -n "$DD_HOME" ]; then
    dd_home=$DD_HOME
fi

unamestr=`uname`

if [ $(which curl) ]; then
    dl_cmd="curl -k -L -o"
else
    dl_cmd="wget -O"
fi

# create home base for the agent
if [ $apikey ]; then
    if [ $dd_home ]; then
  dd_base=$dd_home
    else
  if [ "$unamestr" = "SunOS" ]; then
      dd_base="/opt/local/datadog"
  else
      dd_base=$HOME/.datadog-agent
  fi
    fi
else
    if [ $dd_home ]; then
  dd_base=$dd_home
    else
  if [ "$unamestr" = "SunOS" ]; then
      dd_base="/opt/local/datadog"
  else
      dd_base=$HOME/.pup
  fi
    fi
fi
mkdir -p $dd_base

# set up a virtual env
$dl_cmd $dd_base/virtualenv.py https://raw.github.com/pypa/virtualenv/develop/virtualenv.py
python $dd_base/virtualenv.py $dd_base/venv
. $dd_base/venv/bin/activate

# install dependencies
pip install tornado

# figure out where to pull from
tag="3.5.1"

# set up the agent
mkdir -p $dd_base/agent
$dl_cmd $dd_base/agent.tar.gz https://github.com/DataDog/dd-agent/tarball/$tag
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

# This is the script that will be used by SMF
if [ "$unamestr" = "SunOS" ]; then
    cp $dd_base/agent/packaging/datadog-agent/smartos/dd-agent $dd_base/bin/dd-agent
    chmod +x $dd_base/bin/dd-agent
fi

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

# on solaris, skip the test
# just svcadm
if [ "$unamestr" = "SunOS" ]; then
    svccfg import $dd_base/agent/packaging/datadog-agent/smartos/dd-agent.xml
    svcadm enable site/datadog
    svcs datadog

		printf "*** The agent is running. My work on this planet is done... ( ^_^)／ ***"
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
         "
	  # kthxbye
	  exit $?
else
    # run agent
    cd $dd_base
    supervisord -c $dd_base/supervisord/supervisord.conf > /dev/null 2>&1 &
    agent_pid=$!
    trap "{ kill $agent_pid; exit 255; }" INT TERM
    trap "{ kill $agent_pid; exit; }" EXIT
    
    # regular agent install
    if [ $apikey ]; then
    
        # wait for metrics to be submitted
        printf "\033[32m
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
    
        curl -f http://localhost:17123/status?threshold=0 > /dev/null 2>&1
        success=$?
        while [ "$success" -gt "0" ]; do
            sleep 1
            echo -n "."
            curl -f http://localhost:17123/status?threshold=0 > /dev/null 2>&1
            success=$?
        done
    
        # print instructions
        printf "\033[32m
    
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
    
        printf "\033[0m"
    
    # pup install
    else
    
        # print instructions
        printf "\033[32m
    
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
    
        printf "\033[0m"
    fi
    
    wait $agent_pid
fi
