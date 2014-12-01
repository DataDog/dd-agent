# stdlib
import time
from hashlib import md5
import urllib2

# project
from checks import AgentCheck
from util import headers

# 3rd party
import simplejson as json
import requests

class Marathon(AgentCheck):

    check_name = "marathon.can_connect"

    def check(self, instance):
        if 'url' not in instance:
            raise Exception('Marathon instance missing "url" value.')

        # Load values from the instance config
        url = instance['url']
        instance_tags = instance.get('tags', [])
        default_timeout = self.init_config.get('default_timeout', 5)
        timeout = float(instance.get('timeout', default_timeout))

        response = self.get_v2_apps(url, timeout)
        if response is not None:
            self.gauge('marathon.apps', len(response['apps']), tags=instance_tags)
            for app in response['apps']:
                tags = ['app_id:' + app['id'], 'version:' + app['version']] + instance_tags
                for attr in ['taskRateLimit','instances','cpus','mem','tasksStaged','tasksRunning']:
                    if hasattr(app, attr):
                        self.gauge('marathon.' + attr, app[attr], tags=tags)
                    else:
                        self.warning('Marathon application (id: %s) has no attribute %s' % (app['id'], attr))
                versions_reply = self.get_v2_app_versions(url, app['id'], timeout)
                if versions_reply is not None:
                    self.gauge('marathon.versions', len(versions_reply['versions']), tags=tags)

    def get_v2_apps(self, url, timeout):
        # Use a hash of the URL as an aggregation key
        aggregation_key = md5(url).hexdigest()
        tags = ['url:%s' % url]
        msg = None
        status = None
        try:
            r = requests.get(url + "/v2/apps", timeout=timeout)
            if r.status_code != 200:
                self.status_code_event(url, r, aggregation_key)
                status = AgentCheck.CRITICAL
                msg = "Got %s when hitting %s" % (r.status_code, url)
        except requests.exceptions.Timeout as e:
            # If there's a timeout
            self.timeout_event(url, timeout, aggregation_key)
            msg = "%s seconds timeout when hitting %s" % (timeout, url)
            status = AgentCheck.CRITICAL
        except Exception as e:
            msg = e.message
            status = AgentCheck.CRITICAL
        finally:
            if status is AgentCheck.CRITICAL:
                self.service_check(self.check_name, status, tags=tags, message=msg)
                raise Exception(msg)

        req_json = r.json()
        app_count = len(req_json['apps'])

        if app_count is 0:
            status = AgentCheck.WARN
            msg = "No marathon applications detected at %s" % url
        else:
            instance_count = 0
            for app in req_json['apps']:
                instance_count += app['instances']
            status = AgentCheck.CRITICAL if instance_count is 0 else AgentCheck.OK
            msg = "%s Marathon app(s) detected with %s instances running at %s" % (app_count, instance_count, url)


        self.service_check(self.check_name, status, tags=tags, message=msg)

        return req_json

    def get_v2_app_versions(self, url, app_id, timeout):
        # Use a hash of the URL as an aggregation key
        aggregation_key = md5(url).hexdigest()

        try:
            r = requests.get(url + "/v2/apps/" + app_id + "/versions", timeout=timeout)
        except requests.exceptions.Timeout as e:
            # If there's a timeout
            self.timeout_event(url, timeout, aggregation_key)
            self.warning("Timeout when hitting %s" % url)
            return None

        if r.status_code != 200:
            self.status_code_event(url, r, aggregation_key)
            self.warning("Got %s when hitting %s" % (r.status_code, url))

        return r.json()

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
