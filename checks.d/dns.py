import time
import socket

from checks import AgentCheck
from hashlib import md5

class DNSCheck(AgentCheck):
    def check(self, instance):
        if 'hostname' not in instance:
            self.log.info("Skipping instance, no hostname found.")
            return

        # Load values from the instance config
        hostname = instance['hostname']
        default_timeout = self.init_config.get('default_timeout', 5)
        timeout = float(instance.get('timeout', default_timeout))

        # Use a hash of the hostname as an aggregation key
        aggregation_key = md5(hostname).hexdigest()

        # Check the hostame
        start_time = time.time()
        try:
            r = socket.gethostbyname(hostname)
            end_time = time.time()
        except socket.exceptions.timeout as e:
            # If there's a timeout
            self.timeout_event(hostname, timeout, aggregation_key)
            return
        except socket.exceptions.herror as he:
            # If there's a resolution error e.g. "no such hostname"
            self.status_code_event(hostname, socket.exceptions.herror, aggregation_key)

        timing = end_time - start_time
        self.gauge('dns.response_time', timing, tags=['dns_check'])

    def timeout_event(self, hostname, timeout, aggregation_key):
        self.event({
            'timestamp': int(time.time()),
            'event_type': 'dns_check',
            'msg_title': 'DNS resolve timeout',
            'msg_text': '%s timed out after %s seconds.' % (hostname, timeout),
            'aggregation_key': aggregation_key
        })

    def status_code_event(self, hostname, herror, aggregation_key):
        self.event({
            'timestamp': int(time.time()),
            'event_type': 'dns_check',
            'msg_title': 'Invalid reponse code for %s' % hostname,
            'msg_text': '%s returned a status of %s' % (hostname, herror.string),
            'aggregation_key': aggregation_key
        })

if __name__ == '__main__':
    check, instances = DNSCheck.from_yaml('/etc/dd-agent/conf.d/dns.yaml')
    for instance in instances:
        print "\nRunning the check against hostname: %s" % (instance['hostname'])
        check.check(instance)
        if check.has_events():
            print 'Events: %s' % (check.get_events())
        print 'Metrics: %s' % (check.get_metrics())