import sys
import os
import subprocess
import ConfigParser

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

def run_plugin(script, runner, metrics):
    p = subprocess.Popen([runner, script], stdout= subprocess.PIPE)
    res = p.communicate()

    local_metrics = {}
    if p.returncode == 0:
        for line in res[0].splitlines(True):
            try:
                metric, value = line.split(' ', 1)
                # Remove value to metric name
                if metric.endswith(".value"):
                    metric = metric[:-6]

                local_metrics[metric] = float(value)
            except:
                pass

    index, values = parse_metrics(script, local_metrics)
    if index is not None and values is not None:
        if metrics.has_key(index):
            rUpdate(metrics[index], values)
        else:
            metrics[index] = values

def run_plugins(prunner, ppath):
    
    metrics = {}

    # Parse and run the scripts
    for script in os.listdir(ppath):
        # Check if the file is executable
        if os.access(os.path.join(ppath,script), os.X_OK):
            run_plugin(script, prunner, metrics)

    print metrics['postgres']

if __name__ == "__main__":
    
    if len(sys.argv) != 3:
        usage()
        sys.exit(1)

    run_plugins(sys.argv[1],sys.argv[2])
