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

        func(*args, **kwargs)

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

    return wrapped_func
