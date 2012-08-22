#! /usr/bin/python

import sys
import fcntl
import os
import select
import subprocess
import ConfigParser
import inspect
import imp
from datetime import datetime, timedelta
from cStringIO import StringIO
from checks import Check

def usage():
    print sys.argv[0], "[munin-run path]", "[plugin directory]"

def run_plugin(script, real_name, runner):
    """Print the section, run the plugin
     real_name is the script real name (without path): munin plugin are
    often using their name for parameters: postgres_connections_db points
    to postgres_connections_ and db is the name of the database
    """
    print "[%s %s]" % (script, real_name)
    sys.stdout.flush()
    subprocess.call([runner, script], stdout= sys.stdout)

def run_plugins(prunner, ppath):
    "Parse plugin directory and run all executable plugins"
    # Parse and run the scripts
    for script in os.listdir(ppath):
        # Check if the file is executable
        path = os.path.join(ppath,script)
        if os.access(path, os.X_OK):
            run_plugin(script, os.path.basename(os.path.realpath(path)), prunner)

class Munin(Check):

    def __init__(self, logger):
        Check.__init__(self, logger)
        self._current_plugin = None
        self._current_device = None
        self._current_parser = None
        self._current_mgraph = None
        self._myself = os.path.abspath(inspect.getfile(inspect.currentframe()))

        # Init parsers
        self._parsers = {}
        d = os.path.dirname(os.path.abspath(__file__))
        self.logger.info("Looking for plugins in: %s" % d)
        for m in os.listdir(d):
            m = os.path.join(d,m)
            name, ext = os.path.splitext(os.path.split(m)[-1])
            if ext.lower() == ".py" and name not in ['__init__', "munin"]:
                try:
                    pclass = name.capitalize() + 'MuninPlugin'
                    module = imp.load_source(pclass, os.path.abspath(m))
                    if hasattr(module, pclass):
                        inst = getattr(module,pclass)() 
                        self._parsers[inst.get_name()] = inst.parse_metric
                        self.logger.info("Registered plugin for %s" % inst.get_name())
                except:
                    self.logger.exception("Failed loading plugin from %s" % m)

    def register_metric(self,mname):
        if not self.is_counter(mname):
            self.counter(mname)

    # plugins are static and the check object is the first argument, hence the static
    # with a self
    @staticmethod 
    def default_metric_parser(self, section, device, name, value, mgraph = None):
        """Fallback: register metric as a counter, prefix it by munin.
        """
        
        mname = "munin." + section + "." + name
        if mgraph is not None:
            mname = mname + "." + mgraph
        self.register_metric(mname)
        if device is None:
          print "Saving:", mname, value, device
        self.save_sample(mname,value)

    def read_metric(self, line):
        """Read one metric line, send it to the parser"""
        try:
            metric, value = line.split()
            if metric.endswith('.value'):
                metric = metric[0:-6]
            self._current_parser(self, self._current_plugin, self._current_device,
                                metric, float(value), mgraph = self._current_mgraph)
        except Exception, e:
            self.logger.exception(e)
            return

    def end_plugin(self):
        """Reset plugin state"""
        self._current_plugin = None
        self._current_parser = None
        self._current_device = None
        self._current_mgraph = None

    def start_plugin(self, name, script_real_name):    
        """Set up new metric context for a plugin"""
        self.end_plugin()

        if name != script_real_name:
            self._current_device = name[len(script_real_name):]
            self._current_plugin = script_real_name.rstrip('_')
        else: 
            self._current_plugin = name

        self._current_parser = self.default_metric_parser
        for parser in self._parsers:
            if self._current_plugin.startswith(parser):
                self._current_parser = self._parsers[parser]
                break

    def process_metric_line(self, line):
        """Parse a line sent by munin.py while running plugins:
            a line with brackets denotes a section (the plugin name)
            It is followed by 0 or more line of metrics"""
        #print line
        if len(line) > 0:
            if line[0] == '[' and line[-1] == ']':
                section, script_real_name = line[1:-1].split(' ')
                self.start_plugin(section, script_real_name)
            elif line.startswith("multigraph "):
                self._current_mgraph = line.split('_',1)[1]
            elif self._current_plugin is not None:
                self.read_metric(line)

    def run_with_timeout(self, cmd, timeout, callback):
        """Run a subprocess for at max timeout seconds, calling
        'callback' for each line read from stdout"""

        self.logger.info("Munin: Running: %s" % cmd)

        # Run the process. Add the current datadog root as PYTHONPATH for imports
        # to work. This is the first entry of the current sys.path
        p = subprocess.Popen(cmd, stdout = subprocess.PIPE, 
            env={'PYTHONPATH': os.path.abspath(os.environ.get("PYTHONPATH",sys.path[0]))})

        fcntl.fcntl(p.stdout.fileno(),
                fcntl.F_SETFL,
                fcntl.fcntl(p.stdout.fileno(), fcntl.F_GETFL) | os.O_NONBLOCK)

        self._buf = StringIO()

        def updateChunck(chunck):
            for c in chunck:
                if c == '\n':
                    callback(self._buf.getvalue())
                    self._buf = StringIO()
                else:
                    self._buf.write(c)            

        started = datetime.now()
        to = timedelta(seconds = timeout)

        while True:
            readx = select.select([p.stdout.fileno()], [], [], 0.2)[0]
            if readx:
                chunk = p.stdout.read()
                updateChunck(chunk)
            if p.poll() is not None:
                break
            if (datetime.now() - started) > to:
                self.logger.info("Running for too long, stop")
                p.terminate()
                break

        # Don't forget to flush the last plugin
        self.end_plugin()
        self.logger.info("Munin: done")

    def check(self, config):
        """As usual, called by the agent"""
        prun = config.get("munin_runner", "/usr/sbin/munin-run")
        ppdir = config.get("munin_plugin_path", "/etc/munin/plugins")
        timeout = config.get("munin_timeout",60)

        #Check that prun exists
        if not os.path.exists(prun):
            return False

        #Check that prun is executable
        if os.access(prun, os.X_OK):
            try:
                self.run_with_timeout(["/usr/bin/sudo", self._myself, prun, ppdir], timeout, self.process_metric_line)
                return self.get_metrics()
            except:
                self.logger.exception("Cannot get munin stats")
                return False
        else:
            self.logger.warn("Munin runner is not executable. Please check agent configuration")
            return False

if __name__ == "__main__":
    
    if len(sys.argv) == 3:
        run_plugins(sys.argv[1],sys.argv[2])
    else:
        import logging
        config = { "apikey": "toto" }
        munin = Munin(logging)
        print munin.check(config) 
        #print munin.check(config) 
