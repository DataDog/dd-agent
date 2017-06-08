# stdlib
import time

# 3rd party
try:
    import psutil
except ImportError:
    psutil = None

# project
from checks import AgentCheck


class MemorySnapshot(AgentCheck):
    def __init__(self, name, init_config, agentConfig, instances=None):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances=instances)
        if instances is not None and len(instances) > 1:
            raise Exception("Memory snapshot check only supports one configured instance.")

        self.triggered = False

    def check(self, instance):
        if psutil is None:
            self.log.debug("psutil is not available, skipping check")
            return

        trigger_threshold = float(instance.get('trigger_threshold', 90.0))
        max_cmd_line_args = int(instance.get('max_cmd_line_args', 3))
        mem_per_process_threshold = float(instance.get('memory_per_process_threshold', 100.0))
        max_process_count = int(instance.get('max_process_count', 10))

        cur_memory_usage_pct = psutil.virtual_memory().percent
        if cur_memory_usage_pct > trigger_threshold:
            if not self.triggered:

                # Send an event only one we cross the threshold
                self.triggered = True
                processes = []
                for proc in psutil.process_iter():
                    try:
                        pinfo = proc.as_dict(attrs=['pid', 'cmdline', 'memory_info'])
                    except psutil.NoSuchProcess:
                        continue
                    mem_in_mb = float(pinfo['memory_info'].rss) / (1024 ** 2)
                    if mem_in_mb > mem_per_process_threshold:
                        processes.append((pinfo['pid'], " ".join(pinfo['cmdline'][:max_cmd_line_args]), mem_in_mb))

                processes = sorted(processes, key=lambda x:-x[2])[:max_process_count]
                max_cmd_len = max([len(k[1]) for k in processes])

                event_text = """%%%
```
| pid | command {0}| rss |
|-----|-{1}-|-----|
""".format("-" * (max_cmd_len - 7), "-" * max_cmd_len)

                for p in processes:
                    event_text += "{0} |{1}| {2} MB\n".format(p[0], p[1] + " " * (max_cmd_len - len(p[1])), int(p[2]))

                event_text += "```\n%%%"
                self.event({
                    'timestamp': time.time(),
                    'hostname': self.hostname,
                    'msg_title': "Memory usage is high ({0}%) on {1}".format(
                        cur_memory_usage_pct, self.hostname),
                    'msg_text': event_text,
                    'event_type': "memory_snapshot",
                    "source_type_name": "memory_snapshot",
                    "event_object": "memory_snapshot-{0}".format(self.hostname),
                    "tags": ["memory_usage"],
                })

        else:
            self.triggered = False
