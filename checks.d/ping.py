#!/usr/bin/python

from checks import AgentCheck
import subprocess
import time

class PingCheck(AgentCheck):
  def __init__(self, name, init_config, agentConfig):
    AgentCheck.__init__(self, name, init_config, agentConfig)

  def check(self, instance):
    ip = instance['ip']
    name = instance['name']

    try:
      var = subprocess.check_output('ping -q -c 3 -t 20 ' + ip, shell=True).splitlines(True)

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

    self.gauge('ping.min', min, ["destination:" + name])
    self.gauge('ping.avg', avg, ["destination:" + name])
    self.gauge('ping.max', max, ["destination:" + name])
    self.gauge('ping.jitter', jitter, ["destination:" + name])
    self.gauge('ping.loss', loss, ["destination:" + name])

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
