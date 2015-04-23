#3p
import psutil

import os
import logging
from config import _is_affirmative

log = logging.getLogger('collector')
PSTATS_LIMIT = 20

def wrap_profiling(func):
    """
    Wraps the function call in a cProfile run, processing and logging the output with pstats.Stats

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
            ps.print_stats(PSTATS_LIMIT)
            log.info(s.getvalue())
        except Exception:
            log.warn("Cannot disable profiler")

        return ret_val

    return wrapped_func
