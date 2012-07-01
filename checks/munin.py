import sys
import os
import subprocess
import ConfigParser

def usage():
    print sys.argv[0], "[munin-run path]", "[plugin directory]"

def run_plugin(script, runner):
    print "Running:", script
    p = subprocess.Popen([runner, script], stdout= subprocess.PIPE)
    res = p.communicate()
    if p.returncode == 0:
        for line in res[0].splitlines(True):
            try:
                metric, value = line.split(' ', 1)
                value = float(value)
                print "Metric:", metric, " value:", value
            except:
                pass

def run_plugins(prunner, ppath):
    
    # Parse and run the scripts
    for script in os.listdir(ppath):
        # Check if the file is executable
        if os.access(os.path.join(ppath,script), os.X_OK):
            run_plugin(script, prunner)

if __name__ == "__main__":
    
    if len(sys.argv) != 3:
        usage()
        sys.exit(1)

    run_plugins(sys.argv[1],sys.argv[2])
