# Copyright 2013 Patrick Galbraith 
#
# Author: Patrick Galbraith <patg@patg.net> 
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
from checks import AgentCheck
import subprocess, os
import sys
import re
import gearman
import time

class Gearman(AgentCheck):
    def __init__(self, name, init_config, agentConfig):
        AgentCheck.__init__(self, name, init_config, agentConfig)
        self.gearman_version = None
        self.gman_adm_client = None

    def _get_status(self):
        status_tuple = () 
        if self.gman_adm_client is not None:
            self.log.debug("Collecting data from gearman")
            try:
		status_tuple = self.gman_adm_client.get_status()
		print "status response " 
		print status_tuple
                self.log.debug("Collecting done. status:")
       		self.log.debug(status_tuple)
            except:
                if self.log is not None:
                    self.log.exception("While running get_status()")
    
        return status_tuple


    def getVersion(self):
        # Get Gearman version
        if self.gearman_version == None and self.gman_adm_client is not None:
            try:
		version_response = self.gman_adm_client.get_version()
		self.log.debug("version: %s" % version_response)
                version_ar = version_response.split(' ')
               
                self.gearman_version = version_ar[1]
            except: 
                self.log.exception('Gearman Admin error when getting version')

        return self.gearman_version

    def _get_server_pid(self):
 
        pid = None

        try:
            if sys.platform.startswith("linux"):
                ps = subprocess.Popen(['ps','-C','gearmand','-o','pid'], stdout=subprocess.PIPE, 
                                      close_fds=True).communicate()[0]
                pslines = ps.split('\n')
                # First line is header, second line is gearman pid
                if len(pslines) > 1 and pslines[1] != '':
                    return int(pslines[1])

            elif sys.platform.startswith("darwin") or sys.platform.startswith("freebsd"):
                # Get all processes, filter in python then
                procs = subprocess.Popen(["ps", "-A", "-o", "pid,command"], stdout=subprocess.PIPE, 
                                         close_fds=True).communicate()[0]
                ps = [p for p in procs.split("\n") if p.index("gearmand") > 0]
                if len(ps) > 0:
                    return int(ps.split())[0]
            else:
                self.log.warning("Unsupported platform gearmand pluging")
        except:
            if self.log is not None:
                self.log.exception("while fetching gearmand pid from ps")
            
        return pid

    def _collect_procfs(self, tags):
        # Try to use the pid file, but there is a good chance
        # we don't have the permission to read it
        pid_file = None
        pid = None

        self.log.debug("pid file: %s" % str(pid_file))
 
        try:
            f = open(pid_file)
            pid = int(f.readline())
            f.close()
        except:
            if self.log is not None:
                self.log.warn("Cannot compute advanced gearman metrics; cannot read gearman pid file %s" % pid_file)

        self.log.debug("pid: %s" % pid)
        # If pid has not been found (permission issue), read it from ps

        if pid is None:
            pid = self._get_server_pid()
            self.log.debug("pid: %s" % pid)

        if pid is not None:
            # At last, get gearman cpu data out of procfs
            try:
                # See http://www.kernel.org/doc/man-pages/online/pages/man5/proc.5.html
                # for meaning: we get 13 & 14: utime and stime, in clock ticks and convert
                # them with the right sysconf value (SC_CLK_TCK)
                f = open("/proc/" + str(pid) + "/stat")
                data = f.readline()
                f.close()
                fields = data.split(' ')
                ucpu = fields[13]
                kcpu = fields[14]
                clk_tck = os.sysconf(os.sysconf_names["SC_CLK_TCK"])

                # Convert time to s (number of second of CPU used by gearman)
                # It's a counter, it will be divided by the period, multiply by 100
                # to get the percentage of CPU used by gearman over the period
                self.rate("gearman.user_time", int((float(ucpu)/float(clk_tck)) * 100), tags=tags)
                self.rate("gearman.kernel_time", int((float(kcpu)/float(clk_tck)) * 100), tags=tags)

            except:
                if self.log is not None:
                    self.log.exception("While reading gearman (pid: %s) procfs data" % pid)

    def check(self, instance):
        import pprint
        import logging
        logging.basicConfig(level=logging.DEBUG)
        pprint.pprint(instance)
        self.log.debug("Gearman check start")
        try:
            host = instance.get('server', '')
            port = instance.get('port', '')
            if host == '':
                host = '127.0.0.1'
            if port == '':
                port = '4730' 

            tags = instance.get('tags', [])
            options = instance.get('options', {})
            self.log.debug("OPTIONS")
            self.log.debug(options)

            # Connect
            try:
                self.log.debug("connecting to gearman GearmanAdminClient([\"%s:%s\"])" % (host, port))
                self.gman_adm_client = gearman.GearmanAdminClient(["%s:%s" % (host, port)])
                self.getVersion()
            except ImportError, e:
                self.log.exception("Cannot import 'gearman' client lib")
                return False
                
            self.log.debug("Connected to gearman")
    
            # Metric collection
            self.log.debug("gearman version %s" % self.gearman_version)

	    running = queued = 0
            unique_tasks = 0
            status_tuple = self._get_status()
            for stat in status_tuple:
                running += stat['running']
                queued += stat['queued']

            unique_tasks = len(status_tuple)

            self.log.debug("running %d, queued %d, unique_tasks %d" % (running, queued, unique_tasks))
    
	    self.gauge("gearman.unique_tasks", unique_tasks, tags=tags)
	    self.gauge("gearman.running", running, tags=tags)
	    self.gauge("gearman.queued", queued, tags=tags)
    
            self.log.debug("Collect cpu stats")
            self._collect_procfs(tags=tags)

            self.log.debug("Done with gearman agent")

        except:
            self.log.exception("Cannot check gearman")
            return False

if __name__ == "__main__":
    import pprint
    check, instances = Gearman.from_yaml('/etc/dd-agent/conf.d/gearmand.yaml')
    for instance in instances:
        print "\nRunning the check against url: %s" % (instance['server'])
        pprint.pprint(check.check(instance))
        if check.has_events():
            print 'Events: %s' % (check.get_events())
        print 'Metrics: %s' % (check.get_metrics())
