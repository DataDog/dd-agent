#!/usr/bin/env python

"""DataDog agent checks for system.vm proc info."""

from checks import AgentCheck


def valid_instance(instance):
    return "proc" in instance or "vmstat" in instance


class LinuxVm(AgentCheck):
    VM_BASE = "system.vm"

    def check(self, instance):
        if not valid_instance(instance):
            return

        proc = instance.get("proc", {})
        vmstat = instance.get("vmstat", {})

        if proc:
            for gauge in proc.get("gauges", []):
                self.proc(self.gauge, gauge)

            for counter in proc.get("counts", []):
                self.proc(self.count, counter)

        if vmstat:
            vmstats = {x: int(y) for x, y in map(str.split, open("/proc/vmstat").readlines())}
            print vmstats
            for gauge in vmstat.get("gauges", []):
                self.vm(self.gauge, gauge, vmstats)

            for counter in vmstat.get("counts", []):
                self.vm(self.count, counter, vmstats)

    def proc(self, metfunc, path):
        try:
            value = float(open(path).read().strip())
            name = path.rstrip('/').split('/')[-1]
            metfunc("%s.%s" % (self.VM_BASE, name), value)
        except Exception as e:
            self.log.error(e)

    def vm(self, metfunc, stat, stats):
        if stat not in stats:
            return
        metfunc("%s.%s" % (self.VM_BASE, stat), stats[stat])
