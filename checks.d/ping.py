from checks import AgentCheck

import subprocess
import time

class PingCheck(AgentCheck):
    def check(self, instance):
        if 'name' not in instance:
            raise Exception('Skipping instance, name not defined.')

        if 'ip' not in instance:
            raise Exception('Skipping instance, ip not defined.')

        name = instance['name']
        ip = instance['ip']

        tags = instance.get('tags', [])
        tags = tags + ['destination:' + name, 'ip:' + ip]

        try:
            var = subprocess.check_output('ping -q -c 5 -t 20 ' + ip, shell=True).splitlines(True)

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

        except:
            (min, avg, max, jitter,loss) = ('0', '0', '0', '0', '100')

        self.gauge('ping.min', min, tags)
        self.gauge('ping.avg', avg, tags)
        self.gauge('ping.max', max, tags)
        self.gauge('ping.jitter', jitter, tags)
        self.gauge('ping.loss', loss, tags)

        if float(loss) > 0:
            self.event({
                'timestamp': int(time.time()),
                'event_type': 'ping_check',
                'api_key': self.agentConfig.get('api_key', ''),
                'msg_title': loss + '% packet loss on ' + name,
                'msg_text': loss + '% packet loss on ' + name,
                'aggregation_key': ip + name + loss,
                'alert_type': 'warning'
            })
