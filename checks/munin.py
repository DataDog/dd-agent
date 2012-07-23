#! /usr/bin/python

import sys
import fcntl
import os
import select
import subprocess
import ConfigParser
from datetime import datetime, timedelta

from checks import Check

def usage():
    print sys.argv[0], "[munin-run path]", "[plugin directory]"

def rUpdate(targetDict, itemDict):
    "Recursively updates nested dicts"
    for key, val in itemDict.items():
        if type(val) == type({}):
            newTarget = targetDict.setdefault(key,{})
            rUpdate(newTarget, val)
        else:
            targetDict[key] = val

def run_plugin(script, runner):
    "Print the section, run the plugin"
    print "[%s]" % script
    sys.stdout.flush()
    subprocess.call([runner, script], stdout= sys.stdout)

def run_plugins(prunner, ppath):
    "Parse plugin directory and run all executable plugins"
    # Parse and run the scripts
    for script in os.listdir(ppath):
        # Check if the file is executable
        if os.access(os.path.join(ppath,script), os.X_OK):
            run_plugin(script, prunner)

class Munin(Check):

    def __init__(self, logger):
        Check.__init__(self, logger)
        self._current_plugin = None
        self._current_metrics = None
        self._parsers = {}

    def default_metric_parser(self, section, metrics):
        "Fallback: just a pass through. Prefix metric by munin"
        
        return "munin." + section, metrics

    def parse_metrics(self, section, metrics):
        """Find the correct parser and run it against the
            dict of collected metrics"""
        # Find metric parser
        p = self.default_metric_parser
        for parser in self._parsers:
            if section.startswith(parser):
                p = self._parsers[parser]
   
        return p(section, metrics)

    def read_metric(self, line):
        """Read one metric line, append it to the current metric dict:
            a line is metric_name.value = value"""
        try:
            metric, value = line.split()
            if metric.endswith('.value'):
                metric = metric[0:-6]
        except Exception, e:
            #Invalid metric
            return

        self._current_metrics[metric] = value

    def end_plugin(self):
        """Flush current plugin metric dict: parse metrics and send
            them back to the agent"""
        if self._current_plugin is not None:

            print self.parse_metrics(self._current_plugin,self._current_metrics)
            self._current_plugin = None
            self._current_metrics = None

    def start_plugin(self, name):    
        """Set up new metric context for a plugin"""
        self.end_plugin()
        self._current_plugin = name
        self._current_metrics = {}

    def process_metric_line(self, line):
        """Parse a line sent by munin.py while running plugins:
            a line with brackets denotes a section (the plugin name)
            It is followed by 0 or more line of metrics"""
        if len(line) > 0:
            if line[0] == '[' and line[-1] == ']':
                self.start_plugin(line[1:-1])
            elif self._current_plugin is not None:
                self.read_metric(line)

    def run_with_timeout(self, cmd, timeout, callback):
        """Run a subprocess for at max timeout seconds, calling
        'callback' for each line read from stdout"""
        p = subprocess.Popen(cmd, stdout = subprocess.PIPE)

        fcntl.fcntl(p.stdout.fileno(),
                fcntl.F_SETFL,
                fcntl.fcntl(p.stdout.fileno(), fcntl.F_GETFL) | os.O_NONBLOCK)

        def updateChunck(chunck):
            lines = chunck.split('\n')
            for l in lines:
                callback(l)

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
                p.terminate()
                break

        # Don't forget to flush the last plugin
        self.end_plugin()

    def check(self, config):
        """As usual, called by the agent"""
        prun = config.get("munin_runner", "/usr/sbin/munin-run")
        ppdir = config.get("munin_plugin_path", "/etc/munin/plugins")
        timeout = config.get("munin_timeout",60)

        self.run_with_timeout(["/usr/bin/sudo", sys.argv[0], prun, ppdir], timeout, self.process_metric_line)

if __name__ == "__main__":
    
    if len(sys.argv) == 3:
        run_plugins(sys.argv[1],sys.argv[2])
    else:
        import logging
        config = { "apikey": "toto" }
        munin = Munin(logging)
        print munin.check(config) 
