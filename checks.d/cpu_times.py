import psutil
from checks import AgentCheck

class CPUTimes(AgentCheck):

    def check(self, instance):
        cpu_times = psutil.cpu_times(percpu=True)

        for i, cpu in enumerate(cpu_times):
            for key, value in cpu._asdict().iteritems():
                self.rate(
                    "system.per_cpu.{0}".format(key), 
                    100.0 * value, 
                    tags=["cpu:{0}".format(i)]
                    )
