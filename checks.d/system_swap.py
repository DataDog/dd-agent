from checks import AgentCheck
try:
    import psutil
except ImportError:
    psutil = None

B2MB  = float(1048576)

class SystemSwap(AgentCheck):

    def check(self, instance):
        if not psutil:
            return {}

        swap_mem = psutil.swap_memory()
        self.gauge('system.swap.swapped_in', swap_mem.sin / B2MB)
        self.gauge('system.swap.swapped_out', swap_mem.sout / B2MB)
