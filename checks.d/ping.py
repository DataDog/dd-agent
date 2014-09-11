#!/usr/bin/python

from checks import AgentCheck
import subprocess

class PingCheck(AgentCheck):
  def check(self, instance):
    ip = instance['ip']
    name = instance['name']

    try:
      var = subprocess.check_output('ping -q -c 3 -t 20 ' + ip, shell=True).splitlines(True)

      for line in var:
        if "round-trip" in line or "rtt" in line:
          split = line.replace('/',' ').split()
          (min, avg, max, jitter) = (split[6], split[7], split[8], split[9])
    except:
      (min, avg, max, jitter) = (0, 0, 0, 0)

    self.gauge('ping.min', min, ["destination:" + name])
    self.gauge('ping.avg', avg, ["destination:" + name])
    self.gauge('ping.max', max, ["destination:" + name])
    self.gauge('ping.jitter', jitter, ["destination:" + name])
