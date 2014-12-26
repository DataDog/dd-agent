# project
from checks import AgentCheck

# 3rd party
import requests

class Marathon(AgentCheck):

    DEFAULT_TIMEOUT = 5
    SERVICE_CHECK_NAME = 'marathon.can_connect'

    APP_METRICS = ['backoffFactor', 'backoffSeconds', 'cpus', 'dist', 'instances', 'mem', 'taskRateLimit', 'tasksRunning', 'tasksStaged']

    def check(self, instance):
        if 'url' not in instance:
            raise Exception('Marathon instance missing "url" value.')

        # Load values from the instance config
        url = instance['url']
        instance_tags = instance.get('tags', [])
        default_timeout = self.init_config.get('default_timeout', self.DEFAULT_TIMEOUT)
        timeout = float(instance.get('timeout', default_timeout))

        response = self.get_json(url + "/v2/apps", timeout)
        if response is not None:
            self.gauge('marathon.apps', len(response['apps']), tags=instance_tags)
            for app in response['apps']:
                tags = ['app_id:' + app['id'], 'version:' + app['version']] + instance_tags
                for attr in self.APP_METRICS:
                    if attr in app:
                        self.gauge('marathon.' + attr, app[attr], tags=tags)
                versions_reply = self.get_json(url + "/v2/apps/" + app['id'] + "/versions", timeout)
                if versions_reply is not None:
                    self.gauge('marathon.versions', len(versions_reply['versions']), tags=tags)

    def get_json(self, url, timeout):
        try:
            r = requests.get(url, timeout=timeout)
        except requests.exceptions.Timeout:
            # If there's a timeout

            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL,
                message='%s timed out after %s seconds.' % (url, timeout),
                tags = ["url:{}".format(url)])
            raise Exception("Timeout when hitting %s" % url)

        if r.status_code != 200:
            self.status_code_event(url, r)
            raise Exception("Got %s when hitting %s" % (r.status_code, url))

        return r.json()
