# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

"""docker-machine check
Collects metrics from docker-machine
"""

# stdlib
import os
import re
import time

# project
from checks import AgentCheck
from utils.subprocess_output import get_subprocess_output
from config import _is_affirmative

# third party
import json


class DockerMachine(AgentCheck):
    """ Collect metrics and events from docker_machine """

    DEFAULT_DM_CMD = '/usr/bin/docker-machine'
    NAMESPACE = "docker-machine"

    def _collect_raw(self, docker_machine_cmd, instance):
        use_sudo = _is_affirmative(instance.get('use_sudo', False))
        if use_sudo:
            test_sudo = os.system('setsid sudo -l < /dev/null')
            if test_sudo != 0:
                raise Exception('The dd-agent user does not have sudo access')
                docker_machine_cmd = 'sudo' + docker_machine_cmd
        else:
            docker_machine_cmd = docker_machine_cmd

        format_args = instance.get('format_args', [])

        #### Docker machine command example ####
        # docker - machine
        # ls - -format
        # "machine-name: {{.Name}},
        #   status: {{.State}},
        #   is_active:{{.Active}},
        #   error: {{.Error}},
        #   driver_name: {{.DriverName}},
        #   url: {{.URL}},
        #   response_time: {{.ResponseTime}}"

        format_args = ["\"%s\": \"{{.%s}}\"" % (self._convert_camel(k), k) for k in format_args]
        args = docker_machine_cmd.split() + ["{" + ",".join(format_args) + "},"]

        try:
            output, _, _ = get_subprocess_output(args, self.log)
            output = '[{}]'.format(output).replace(",\n]", "]")
            res = json.loads(output)
            return res
        except Exception as e:
            return None
            self.log.warning('Unable to parse data from cmd=%s: %s' % (args, str(e)))

    def _publish(self, raw, func, keyspec, tags):
        try:
            for k in keyspec:
                raw = raw[k]
            func(self.NAMESPACE + '.' + k, raw, tags)
        except KeyError:
            return

    def _extract_metrics(self, raw, instance):
        running_dms = 0
        stopped_dms = 0
        check_name = '{}.checks'.format(self.NAMESPACE)

        for dm in raw:
            tags = []
            dm_state = str(dm['state']).lower()
            tags.append('{}.name:{}'.format(self.NAMESPACE, dm['name']))
            tags.append('{}.url:{}'.format(self.NAMESPACE, (dm['url'] or "None")))
            tags.append('{}.state:{}'.format(self.NAMESPACE, dm['state']))
            tags.append('{}.driver_name:{}'.format(self.NAMESPACE, dm['driver_name']))
            if dm['error'] is not None:
                tags.append('{}.error:{}'.format(self.NAMESPACE, dm['error']))
            self.gauge(self.NAMESPACE, 1, tags=tags)

            if dm_state == 'running':
                running_dms += 1
                self.service_check(check_name, AgentCheck.OK, tags=tags)
                self.gauge('{}.response_time'.format(self.NAMESPACE), int(filter(str.isdigit, str(dm['response_time']))),
                           tags=tags)
            elif dm_state == 'stopped':
                stopped_dms += 1
                self.service_check(check_name, AgentCheck.CRITICAL, tags=tags)
            else:
                self.service_check(check_name, AgentCheck.UNKNOWN, tags=tags)

        self.gauge(self.NAMESPACE, len(raw), tags=tags)
        self.gauge("{}.running".format(self.NAMESPACE), running_dms, tags=self.NAMESPACE)
        self.gauge("{}.stopped".format(self.NAMESPACE), stopped_dms, tags=self.NAMESPACE)
        self.gauge("{}.unknown".format(self.NAMESPACE), (len(raw) - running_dms - stopped_dms), tags=self.NAMESPACE)

        if running_dms == 0:
            self.log.warn("sending no runner event as there is no running docker machine")
            self._send_no_runner_event(instance)


    def _convert_camel(self, camel_str):
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', camel_str)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

    def _send_no_runner_event(self, instance):
        event = {
            "msg_title": "There's NO docker-machine running on host",
            "msg_text": "Couldn't get any docker machine by running the command {}".format(instance.get('docker_machine_cmd') or self.DEFAULT_DM_CMD),
            "alert_type": "error",
            "event_type": "docker-machine runner error",
            "timestamp": int(time.time()),
            "api_key": "{}".format(instance.get("api_key")),
            "tags": "{}".format(self.NAMESPACE)
        }
        self.event(event)

    def check(self, instance):
        docker_machine_cmd = instance.get('docker_machine_cmd') or self.DEFAULT_DM_CMD
        raw = self._collect_raw(docker_machine_cmd, instance)

        if raw is None or len(raw) == 0:
            self._send_no_runner_event(instance)
            self.log.warn("sending no runner event")
        else:
            self._extract_metrics(raw, instance)


if __name__ == '__main__':
    check, instances = DockerMachine.from_yaml('/opt/datadog-agent/etc/conf.d/docker_machine.yaml')
    for i in instances:
        check.check(i)
