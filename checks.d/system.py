from checks import AgentCheck
import psutil

COEFF = 1000.0 * 1000.0 * 1000.0 / 1024.0 / 1024.0 / 1024.0
class SystemCheck(AgentCheck):

    def check(self, instance):
        self.get_cpu_metrics()
        self.get_disk_metrics()

    def get_cpu_metrics(self):
        cpu_times = psutil.cpu_times()

        cpu_metrics = {}
        cpu_metrics['user'] = cpu_times.user + cpu_times.nice
        cpu_metrics['system'] = cpu_times.system + cpu_times.irq + cpu_times.softirq
        cpu_metrics['iowait'] = cpu_times.iowait
        cpu_metrics['idle'] = cpu_times.idle
        cpu_metrics['stolen'] = cpu_times.steal
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




