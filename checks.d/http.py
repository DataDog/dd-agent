import time
import requests

from checks import AgentCheck
from hashlib import md5

class HTTPCheck(AgentCheck):
    def check(self, instance):
        if 'url' not in instance:
            self.log.info("Skipping instance, no url found.")
            return

        # Load values from the instance config
        url = instance['url']
        default_timeout = self.init_config.get('default_timeout', 5)
        timeout = float(instance.get('timeout', default_timeout))

        # Use a hash of the URL as an aggregation key
        aggregation_key = md5(url).hexdigest()

        # Check the URL
        start_time = time.time()
        try:
            r = requests.get(url, timeout=timeout)
            end_time = time.time()
        except requests.exceptions.Timeout as e:
            # If there's a timeout
            self.timeout_event(url, timeout, aggregation_key)
            return

        if r.status_code != 200:
            self.status_code_event(url, r, aggregation_key)

        timing = end_time - start_time
        self.gauge('http.reponse_time', timing, tags=['http_check'])

    def timeout_event(self, url, timeout, aggregation_key):
        self.event({
            'timestamp': int(time.time()),
            'event_type': 'http_check',
            'msg_title': 'URL timeout',
            'msg_text': '%s timed out after %s seconds.' % (url, timeout),
            'aggregation_key': aggregation_key
        })

    def status_code_event(self, url, r, aggregation_key):
        self.event({
            'timestamp': int(time.time()),
            'event_type': 'http_check',
            'msg_title': 'Invalid reponse code for %s' % url,
            'msg_text': '%s returned a status of %s' % (url, r.status_code),
            'aggregation_key': aggregation_key
        })

if __name__ == '__main__':
    check, instances = HTTPCheck.from_yaml('conf.d/http.yaml')
    for instance in instances:
        print "\nRunning the check against url: %s" % (instance['url'])
        check.check(instance)
        if check.has_events():
            print 'Events: %s' % (check.get_events())
        print 'Metrics: %s' % (check.get_metrics())