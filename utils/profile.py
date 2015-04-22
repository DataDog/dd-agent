#3p
import psutil

import os
import logging
from config import _is_affirmative

log = logging.getLogger('collector')

def wrap_profiling(func):
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
            ps.print_stats()
            log.info(s.getvalue())
        except Exception:
            log.warn("Cannot disable profiler")

        return ret_val

    return wrapped_func

def _psutil_config_to_stats(init_config):
    process_config = init_config.get('process', None)
    assert process_config

    current_process = psutil.Process(os.getpid())
    filtered_methods = [k for k,v in process_config.items() if _is_affirmative(v) and\
                            hasattr(current_process, k)]
    stats = {}

    if filtered_methods:
        for method in filtered_methods:
            method_key = method[4:] if method.startswith('get_') else method
            try:
                stats[method_key] = getattr(current_process, method)()
            except psutil.AccessDenied:
                log.warn("Cannot call psutil method {} : Access Denied".format(method))

    return stats
