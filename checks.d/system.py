from checks import AgentCheck
import psutil

COEFF = 1 / 1024.0
class SystemCheck(AgentCheck):

    def check(self, instance):
        self.get_cpu_metrics()
        self.get_disk_metrics()
        self.get_memory_metrics()

    def get_cpu_metrics(self):
        cpu_times = psutil.cpu_times()

        cpu_metrics = {
            'user': cpu_times.user + cpu_times.nice,
            'system': cpu_times.system + cpu_times.irq + cpu_times.softirq,
            'iowait': cpu_times.iowait,
            'idle': cpu_times.idle,
            'stolen': cpu_times.steal,
        }
        cpu_count = psutil.cpu_count()
        for metric, value in  cpu_metrics.iteritems():
            self.rate("system.cpu.{0}2".format(metric), 100.0 * value / cpu_count)

    def get_disk_metrics(self):
        partitions = psutil.disk_partitions()
        for partition in partitions:
            disk_usage = psutil.disk_usage(partition.mountpoint)
            self.gauge("system.disk.free2", disk_usage.free * COEFF, device_name=partition.device)
            self.gauge("system.disk.total2", disk_usage.total * COEFF, device_name=partition.device)
            self.gauge("system.disk.used2", disk_usage.used * COEFF, device_name=partition.device)
            self.gauge("system.disk.in_use2", disk_usage.percent / 100.0, device_name=partition.device)


    def get_memory_metrics(self):
        virtual_memory = psutil.virtual_memory()
        swap = psutil.swap_memory()

        memory_metrics = {
            'total': virtual_memory.total * COEFF,
            'free': virtual_memory.free * COEFF,
            'buffered': virtual_memory.buffers * COEFF,
            'cached': virtual_memory.cached * COEFF,
            'shared': virtual_memory.shared * COEFF,
            'used': (virtual_memory.total - virtual_memory.free) * COEFF,
            'available': (virtual_memory.free +\
                virtual_memory.buffered + virtual_memory.cached) * COEFF,
        }
        memory_metrics['pct_usable'] = float(memory_metrics['available'])\
       / float(virtual_memory.total)

        swap_metrics = {
            'free': swap.free * COEFF,
            'total': swap.total * COEFF,
            'used': swap.used * COEFF,
            'pct_free': float(swap.free) / float(swap.total),
        }

        for key, value in memory_metrics.iteritems():
            self.gauge("system.mem.{0}2".format(key), value)
        for key, value in swap_metrics.iteritems():
            self.gauge("system.swap.{0}2".format(key), value)



