import time
import requests

from checks import AgentCheck
from util import json, headers
from hashlib import md5
import urllib2

class Mesos(AgentCheck):
    def check(self, instance):
        if 'url' not in instance:
            raise Exception('Mesos instance missing "url" value.')
            return

        # Load values from the instance config
        url = instance['url']
        default_timeout = self.init_config.get('default_timeout', 5)
        timeout = float(instance.get('timeout', default_timeout))

        response = self.get_master_roles(url, timeout)
        if response is not None:
            for role in response['roles']:
                tags = ['mesos','role:' + role['name']]
                self.gauge('mesos.role.frameworks', len(role['frameworks']), tags=tags)
                self.gauge('mesos.role.weight', role['weight'], tags=tags)
                resources = role['resources']
                for attr in ['cpus','mem']:
                    if attr in resources:
                        self.gauge('mesos.role.' + attr, resources[attr], tags=tags)

        response = self.get_master_stats(url, timeout)
        if response is not None:
            for key in iter(response):
                self.gauge('mesos.stats.' + key, response[key], tags=['mesos'])

        response = self.get_master_state(url, timeout)
        if response is not None:
            for attr in ['deactivated_slaves','failed_tasks','finished_tasks','killed_tasks','lost_tasks','staged_tasks','started_tasks']:
                tags = ['mesos']
                self.gauge('mesos.state.' + attr, response[attr], tags=tags)

            for framework in response['frameworks']:
                tags = ['mesos','framework:' + framework['id']]
                resources = framework['resources']
                for attr in ['cpus','mem']:
                    if attr in resources:
                        self.gauge('mesos.state.framework.' + attr, resources[attr], tags=tags)

            for slave in response['slaves']:
                tags = ['mesos','slave:' + slave['id']]
                resources = slave['resources']
                for attr in ['cpus','mem','disk']:
                    if attr in resources:
                        self.gauge('mesos.state.slave.' + attr, resources[attr], tags=tags)

    def get_master_roles(self, url, timeout):
        return self.get_json(url + "/master/roles.json", timeout)

    def get_master_stats(self, url, timeout):
        return self.get_json(url + "/master/stats.json", timeout)

    def get_master_state(self, url, timeout):
        return self.get_json(url + "/master/state.json", timeout)

    def get_json(self, url, timeout):
        # Use a hash of the URL as an aggregation key
        aggregation_key = md5(url).hexdigest()

        try:
            response = requests.get(url, timeout=timeout)
            parsed = response.json()
            return parsed
        except requests.exceptions.Timeout as e:
            # If there's a timeout
            self.timeout_event(url, timeout, aggregation_key)
            return None

        if r.status_code != 200:
            self.status_code_event(url, r, aggregation_key)
            return None


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
    check, instances = Mesos.from_yaml('/etc/dd-agent/conf.d/mesos.yaml')
    for instance in instances:
        print "\nRunning the check against url: %s" % (instance['url'])
        check.check(instance)
        if check.has_events():
            print 'Events: %s' % (check.get_events())

        i = 0
        print 'Metrics:\n'
        for metric in check.get_metrics():
            print "  %d: %s" % (i, metric)
            i += 1