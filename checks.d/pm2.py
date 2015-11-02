#  PYTHONPATH=.:/usr/share/datadog/agent/ python checks.d/pm2.py
import subprocess
import json
import time

from checks import AgentCheck


def load_json(command):
    p = subprocess.Popen(command, stdout=subprocess.PIPE)
    out = p.communicate()[0]
    return json.loads(out)


class Pm2(AgentCheck):

    def check(self, instance):

        for instance in load_json(instance['command'].split(' ')):
            node_app_instance = instance['pm2_env']['NODE_APP_INSTANCE']

            tags = ["node_id:%s" % node_app_instance]

            # cpu, memory, errors, processes, restart
            self.gauge('pm2.processes.cpu'.format(node_app_instance), instance['monit']['cpu'], tags=tags)
            self.gauge('pm2.processes.memory'.format(node_app_instance), instance['monit']['memory'], tags=tags)
            self.gauge('pm2.processes.restart'.format(node_app_instance), instance['pm2_env']['restart_time'], tags=tags)


        self.gauge('pm2.processes.processes', instance['pm2_env']['instances'])

if __name__ == '__main__':
    check, instances = Pm2.from_yaml('conf.d/pm2.yaml')
    for instance in instances:
        print "\nRunning on %s" % instance['command']
        check.check(instance)
        if check.has_events():
            print "Events: %s" % check.get_events()
        print
        for m in check.get_metrics():
            print m

