# stdlib
import time
from hashlib import md5

# project
from checks import AgentCheck

# 3rd party
import simplejson as json
import requests

class Marathon(AgentCheck):

    DEFAULT_TIMEOUT = 5
    SERVICE_CHECK_NAME = 'marathon.can_connect'

    def check(self, instance):
        if 'url' not in instance:
            raise Exception('Marathon instance missing "url" value.')

        # Load values from the instance config
        url = instance['url']
        instance_tags = instance.get('tags', [])
        default_timeout = self.init_config.get('default_timeout', self.DEFAULT_TIMEOUT)
        timeout = float(instance.get('timeout', default_timeout))

        response = self.get_v2_apps(url, timeout)
        if response is not None:
            self.gauge('marathon.apps', len(response['apps']), tags=instance_tags)
            for app in response['apps']:
                tags = ['app_id:' + app['id'], 'version:' + app['version']] + instance_tags
                for attr in ['taskRateLimit', 'instances', 'cpus', 'mem', 'tasksStaged', 'tasksRunning', 'backoffSeconds', 'backoffFactor']:
                    if attr in app:
                        self.gauge('marathon.' + attr, app[attr], tags=tags)
                versions_reply = self.get_v2_app_versions(url, app['id'], timeout)
                if versions_reply is not None:
                    self.gauge('marathon.versions', len(versions_reply['versions']), tags=tags)

    def get_v2_apps(self, url, timeout):
        try:
            r = requests.get(url + "/v2/apps", timeout=timeout)
        except requests.exceptions.Timeout:
            # If there's a timeout
            self.timeout_event(url, timeout)
            raise Exception("Timeout when hitting %s" % url)

        if r.status_code != 200:
            self.status_code_event(url, r)
            raise Exception("Got %s when hitting %s" % (r.status_code, url))

        # Condition for request v1.x backward compatibility
        if hasattr(r.json, '__call__'):
            return r.json()
        else:
            return r.json

    def get_v2_app_versions(self, url, app_id, timeout):
        try:
            r = requests.get(url + "/v2/apps/" + app_id + "/versions", timeout=timeout)
        except requests.exceptions.Timeout:
            # If there's a timeout
            self.timeout_event(url, timeout)
            self.warning("Timeout when hitting %s" % url)
            return None

        if r.status_code != 200:
            self.status_code_event(url, r)
            self.warning("Got %s when hitting %s" % (r.status_code, url))
            return None

        return r.json()

    def timeout_event(self, url, timeout):
        self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL,
            message='%s timed out after %s seconds.' % (url, timeout),
            tags = ["url:{}".format(url)])

    def status_code_event(self, url, r):
        self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL,
            message='%s returned a status of %s' % (url, r.status_code),
            tags = ["url:{}".format(url)])
