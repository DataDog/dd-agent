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

def parse_postgres(section, metrics):
    """ Postgres metrics:
      - section: postgres_[metric type]_[optional database] """

    #print section, metrics

    ignore = mtype = db = None
    if section.count('_') == 1:
        ignore, mtype = section.split('_')
    else:
        ignore, mtype, db = section.split('_',2)

    #print "db:", db

    ms = {}
    for m in metrics:
        if m == db:
            ms[mtype] = metrics[m]
        else:
            ms[mtype + '.' + m] = metrics[m]

    #print ms

    if db is not None:
        return 'postgres', { db: ms }
    else:
        return 'postgres', ms
  
METRIC_PARSERS = {
    'postgres': parse_postgres,
}

def default_metric_parser(section, metrics):
    return section, metrics

def parse_metrics(section, metrics):

    # Find metric parser
    p = default_metric_parser
    for parser in METRIC_PARSERS:
        if section.startswith(parser):
            p = METRIC_PARSERS[parser]
   
    return p(section, metrics)

def rUpdate(targetDict, itemDict):
    "Recursively updates nested dicts"
    for key, val in itemDict.items():
        if type(val) == type({}):
            newTarget = targetDict.setdefault(key,{})
            rUpdate(newTarget, val)
        else:
            targetDict[key] = val

def run_plugin(script, runner):
    print "[%s]" % script
    sys.stdout.flush()
    subprocess.call([runner, script], stdout= sys.stdout)

def run_plugins(prunner, ppath):
    
    # Parse and run the scripts
    for script in os.listdir(ppath):
        # Check if the file is executable
        if os.access(os.path.join(ppath,script), os.X_OK):
            run_plugin(script, prunner)

def run_with_timeout(cmd, timeout, callback):

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


class Munin(Check):

    def __init__(self, logger):
        Check.__init__(self, logger)
        self._current_plugin = None
        self._current_metrics = None

    def read_metric(self, line):
        try:
            metric, value = line.split()
        except Exception, e:
            #Invalid metric
            return

        self._current_metrics[metric] = value

    def end_plugin(self):
        if self._current_plugin is not None:

            print parse_metrics(self._current_plugin,self._current_metrics)
            self._current_plugin = None
            self._current_metrics = None

    def start_plugin(self, name):    
        self.end_plugin()
        self._current_plugin = name
        self._current_metrics = {}

    def process_metric_line(self, line):
        if len(line) > 0:
            if line[0] == '[' and line[-1] == ']':
                self.start_plugin(line[1:-1])
            elif self._current_plugin is not None:
                self.read_metric(line)

    def check(self, config):

        prun = config.get("munin_runner", "/usr/sbin/munin-run")
        ppdir = config.get("munin_plugin_path", "/etc/munin/plugins")
        timeout = config.get("munin_timeout",150)

        run_with_timeout(["/usr/bin/sudo", sys.argv[0], prun, ppdir], timeout, self.process_metric_line)

if __name__ == "__main__":
    
    if len(sys.argv) == 3:
        run_plugins(sys.argv[1],sys.argv[2])
    else:
        import logging
        config = { "apikey": "toto" }
        munin = Munin(logging)
        print munin.check(config) 
