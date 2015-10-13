# Download changes
git clone https://github.com/DataDog/dd-agent.git
cd dd-agent
git checkout zeller/subprocess-custom

# Stop Agent
sudo dd-agent stop

# Install all but the tests
sudo cp checks.d/disk.py /opt/datadog-agent/agent/checks.d/disk.py
sudo cp checks.d/mysql.py /opt/datadog-agent/agent/checks.d/mysql.py
sudo cp checks.d/network.py /opt/datadog-agent/agent/checks.d/network.py
sudo cp checks.d/postfix.py /opt/datadog-agent/agent/checks.d/postfix.py
sudo cp checks.d/varnish.py /opt/datadog-agent/agent/checks.d/varnish.py
sudo cp checks/collector.py /opt/datadog-agent/agent/checks/collector.py
sudo cp checks/system/unix.py /opt/datadog-agent/agent/checks/system/unix.py
sudo cp config.py /opt/datadog-agent/agent/config.py
sudo cp jmxfetch.py /opt/datadog-agent/agent/jmxfetch.py
sudo cp resources/processes.py /opt/datadog-agent/agent/resources/processes.py
sudo cp util.py /opt/datadog-agent/agent/util.py
sudo cp utils/subprocess_output.py /opt/datadog-agent/agent/utils/subprocess_output.py

# Remove old *.pyc
sudo rm /opt/datadog-agent/agent/checks.d/*.pyc
sudo rm /opt/datadog-agent/agent/checks/system/*.pyc
sudo rm /opt/datadog-agent/agent/*.pyc
sudo rm /opt/datadog-agent/agent/resources/*.pyc
sudo rm /opt/datadog-agent/agent/utils/*.pyc

# Remove downloaded git repo
cd ..
rm -rf dd-agent/

# Start Agent
sudo dd-agent start
