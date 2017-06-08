# (C) Datadog, Inc. 2013-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# project
from checks import AgentCheck
from utils.subprocess_output import get_subprocess_output

class ShellCheck(AgentCheck):
    """This check provides metrics from a shell command

    WARNING: the user that dd-agent runs may need sudo access for the shell command
             sudo access is not required when running dd-agent as root (not recommended)
    """

    METRIC_NAME_PREFIX = "shell"

    def get_instance_config(self, instance):
        command = instance.get('command', None)
        metric_name = instance.get('metric_name', None)
        metric_type = instance.get('metric_type', 'gauge')
        tags = instance.get('tags', [])

        if command is None:
            raise Exception("A command must be specified in the instance")

        if metric_name is None:
            raise Exception("A metric_name must be specified in the instance")

        if metric_type != "gauge" and metric_type != "rate":
            message = "Unsupported metric_type: {0}".format(metric_type)
            raise Exception(message)

        metric_name = "{0}.{1}".format(self.METRIC_NAME_PREFIX, metric_name)

        config = {
            "command": command,
            "metric_name": metric_name,
            "metric_type": metric_type,
            "tags": tags
        }

        return config

    def check(self, instance):
        config = self.get_instance_config(instance)
        command = config.get("command")
        metric_name = config.get("metric_name")
        metric_type = config.get("metric_type")
        tags = config.get("tags")

        output, _, _ = get_subprocess_output(command, self.log, True)

        try:
            metric_value = float(output)
        except (TypeError, ValueError):
            raise Exception("Command must output a number.")

        if metric_type == "gauge":
            self.gauge(metric_name, metric_value, tags=tags)

        else:
            self.rate(metric_name, metric_value, tags=tags)
