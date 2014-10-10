from checks import AgentCheck

import subprocess
import time

class PingCheck(AgentCheck):
    def check(self, instance):

        # let's make sure our yaml is proper
        if 'name' not in instance:
            raise Exception('Skipping instance, name not defined.')
        if 'ip' not in instance:
            raise Exception('Skipping instance, ip not defined.')

        # read yaml values
        name = instance['name']
        ip = instance['ip']
        tags = instance.get('tags', [])
        tags = tags + ['destination:' + name, 'ip:' + ip]

        # run ping command, remember if it works or not
        try:
            var = subprocess.check_output('ping -q -c 5 -t 20 ' + ip, shell=True).splitlines(True)
            pingworks = 1
        except:
            (pingworks, var, min, avg, max, jitter, loss) = (0, '', '', '', '', '', '')

        # parse ping output line-by-line
        for line in var:
            if "round-trip" in line or "rtt" in line:
                split = line.replace('/',' ').split()
                (min, avg, max, jitter) = (split[6], split[7], split[8], split[9])

            elif " packets received, " in line:
                split = line.replace('%','').split()
                loss = split[6]

            elif " received, " in line:
                split = line.replace('%','').split()
                loss = split[5]

        # send metrics to home base
        self.gauge('ping.min', min, tags)
        self.gauge('ping.avg', avg, tags)
        self.gauge('ping.max', max, tags)
        self.gauge('ping.jitter', jitter, tags)
        self.gauge('ping.loss', loss, tags)
