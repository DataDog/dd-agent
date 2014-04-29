import time
import requests

from checks import AgentCheck
from util import json, headers
from hashlib import md5
import urllib2

class Marathon(AgentCheck):
    def check(self, instance):
        if 'url' not in instance:
            raise Exception('Marathon instance missing "url" value.')
            return

        # Load values from the instance config
        url = instance['url']
        default_timeout = self.init_config.get('default_timeout', 5)
        timeout = float(instance.get('timeout', default_timeout))

        response = self.get_v2_apps(url, timeout)
        if response is not None:
            self.gauge('marathon.apps', len(response['apps']), tags=['marathon'])
            for app in response['apps']:
                tags = ['marathon', 'app_id:' + app['id'], 'version:' + app['version']]
                for attr in ['taskRateLimit','instances','cpus','mem','tasksStaged','tasksRunning']:
                    self.gauge('marathon.' + attr, app[attr], tags=tags)
                versions_reply = self.get_v2_app_versions(url, app['id'], timeout)
                if versions_reply is not None:
                    self.gauge('marathon.versions', len(versions_reply['versions']), tags=tags)

    def get_v2_apps(self, url, timeout):
        # Use a hash of the URL as an aggregation key
        aggregation_key = md5(url).hexdigest()

        try:
            response = requests.get(url + "/v2/apps", timeout=timeout)
            apps = response.json()
            return apps
        except requests.exceptions.Timeout as e:
            # If there's a timeout
            self.timeout_event(url, timeout, aggregation_key)
            return None

        if r.status_code != 200:
            self.status_code_event(url, r, aggregation_key)
            return None

    def get_v2_app_versions(self, url, app_id, timeout):
        # Use a hash of the URL as an aggregation key
        aggregation_key = md5(url).hexdigest()

        try:
            response = requests.get(url + "/v2/apps/" + app_id + "/versions", timeout=timeout)
            apps = response.json()
            return apps
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
    check, instances = Marathon.from_yaml('/etc/dd-agent/conf.d/marathon.yaml')
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