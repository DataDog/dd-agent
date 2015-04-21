import logging
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
