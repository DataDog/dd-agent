"""
Collects metrics from the gunicorn web server.

http://gunicorn.org/
"""

# stdlib
import os
import sys
import time

# 3p
try:
    import psutil
except ImportError:
    psutil = None

# project
from checks import AgentCheck


class GUnicornCheck(AgentCheck):

    # Config
    PROC_NAME = 'proc_name'

    # Number of seconds to sleep between cpu time checks.
    CPU_SLEEP_SECS = 0.1

    # Worker state tags.
    IDLE_TAGS = ["state:idle"]
    WORKING_TAGS = ["state:working"]

    def get_check_library_info(self):
        try:
            import psutil
        except ImportError:
            return "psutil not found"

        try:
            version = psutil.__version__
        except AttributeError:
            version = "unknown"

        return [("psutil", version)]

    def check(self, instance):
        """ Collect metrics for the given gunicorn instance. """
        if not psutil:
            raise GUnicornCheckError("gunicorn check requires the psutil python package")

        self.log.debug("Running instance: %s", instance)

        # Validate the config.
        if not instance or self.PROC_NAME not in instance:
            raise GUnicornCheckError("instance must specify: %s" % self.PROC_NAME)

        # Load the gunicorn master procedure.
        proc_name = instance.get(self.PROC_NAME)
        master_proc = self._get_master_proc_by_name(proc_name)

        # Fetch the worker procs and count their states.
        worker_procs = master_proc.get_children()
        working, idle = self._count_workers(worker_procs)

        # Submit the data.
        self.log.debug("instance %s procs - working:%s idle:%s" % (proc_name, working, idle))
        self.gauge("gunicorn.workers", working, self.WORKING_TAGS)
        self.gauge("gunicorn.workers", idle, self.IDLE_TAGS)

    @classmethod
    def _count_workers(cls, worker_procs):
        working = 0
        idle = 0

        if not worker_procs:
            return working, idle

        # Count how much sleep time is used by the workers.
        cpu_time_by_pid = {}
        for proc in worker_procs:
            # cpu time is the sum of user + system time.
            try:
                cpu_time_by_pid[proc.pid] = sum(proc.get_cpu_times())
            except psutil.NoSuchProcess:
                self.warning('Process %s disappeared while scanning' % proc.name)
                continue
        
        # Let them do a little bit more work.
        time.sleep(cls.CPU_SLEEP_SECS)

        # Processes which have used more CPU are considered active (this is a very 
        # naive check, but gunicorn exposes no stats API)
        for proc in worker_procs:
            if proc.pid not in cpu_time_by_pid:
                # The process is not running anymore, we didn't collect initial cpu times
                continue

            try:
                cpu_time = sum(proc.get_cpu_times())
            except Exception:
                # couldn't collect cpu time. assume it's dead.
                log.debug("Couldn't collect cpu time for %s" % proc)
                continue
            if cpu_time == cpu_time_by_pid[proc.pid]:
                idle += 1
            else:
                working += 1

        return working, idle

    @classmethod
    def _get_master_proc_by_name(cls, name):
        """ Return a psutil process for the master gunicorn process with the given name. """
        master_name = cls._get_master_proc_name(name)
        master_procs = [p for p in psutil.process_iter() if p.name == master_name]
        if len(master_procs) == 0:
            raise GUnicornCheckError("Found no master process with name: %s" % master_name)
        elif len(master_procs) > 1:
            raise GUnicornCheckError("Found more than one master process with name: %s" % master_name)
        else:
            return master_procs[0]

    @staticmethod
    def _get_master_proc_name(name):
        """ Return the name of the master gunicorn process for the given proc name. """
        # Here's an example of a process list for a gunicorn box with name web1
        # root     22976  0.1  0.1  60364 13424 ?        Ss   19:30   0:00 gunicorn: master [web1]
        # web      22984 20.7  2.3 521924 176136 ?       Sl   19:30   1:58 gunicorn: worker [web1]
        # web      22985 26.4  6.1 795288 449596 ?       Sl   19:30   2:32 gunicorn: worker [web1]
        return  "gunicorn: master [%s]" % name


class GUnicornCheckError(Exception):
    pass

