import os
import logging
import cProfile
import pstats
from cStringIO import StringIO

log = logging.getLogger('collector')

class AgentProfiler(object):
    PSTATS_LIMIT = 20
    DUMP_TO_FILE = True
    STATS_DUMP_FILE = './collector-stats.dmp'

    def __init__(self):
        self._enabled = False
        self._profiler = None

    def enable_profiling(self):
        """
        Enable the profiler
        """
        try:
            if not self._profiler:
                self._profiler = cProfile.Profile()
                profiled = True

            self._profiler.enable()
            log.debug("Agent profiling is enabled")
        except Exception:
            log.warn("Cannot enable profiler")

    def disable_profiling(self):
        """
        Disable the profiler, and if necessary dump a truncated pstats output
        """
        try:
            self._profiler.disable()
            s = StringIO()
            ps = pstats.Stats(self._profiler, stream=s).sort_stats("cumulative")
            ps.print_stats(self.PSTATS_LIMIT)
            log.debug(s.getvalue())
            log.debug("Agent profiling is disabled")
            if self.DUMP_TO_FILE:
                log.debug("Pstats dumps are enabled. Dumping pstats output to {0}"\
                            .format(self.STATS_DUMP_FILE))
                ps.dump_stats(self.STATS_DUMP_FILE)
        except Exception:
            log.warn("Cannot disable profiler")

    @staticmethod
    def wrap_profiling(func):
        """
        Wraps the function call in a cProfile run, processing and logging the output with pstats.Stats
        Useful for profiling individual checks.

        :param func: The function to profile
        """
        def wrapped_func(*args, **kwargs):
            try:
                import cProfile
                profiler = cProfile.Profile()
                profiled = True
                profiler.enable()
                log.debug("Agent profiling is enabled")
            except Exception:
                log.warn("Cannot enable profiler")

            # Catch any return value before disabling profiler
            ret_val = func(*args, **kwargs)

            # disable profiler and printout stats to stdout
            try:
                profiler.disable()
                import pstats
                from cStringIO import StringIO
                s = StringIO()
                ps = pstats.Stats(profiler, stream=s).sort_stats("cumulative")
                ps.print_stats(AgentProfiler.PSTATS_LIMIT)
                log.info(s.getvalue())
            except Exception:
                log.warn("Cannot disable profiler")

            return ret_val

        return wrapped_func
