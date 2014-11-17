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
import logging
log = logging.getLogger('collector')

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
                    self.gauge('marathon.' + attr, app[attr], tags=tags)
                versions_reply = self.get_v2_app_versions(url, app, timeout)
                if versions_reply is not None:
                    self.gauge('marathon.versions', len(versions_reply['versions']), tags=tags)

    def get_v2_apps(self, url, timeout):
        # Use a hash of the URL as an aggregation key
        aggregation_key = md5(url).hexdigest()
        tags = ['url:%s' % url]

        try:
            r = requests.get(url + "/v2/apps", timeout=timeout)
            status = AgentCheck.OK
            if r.status_code != 200:
                self.status_code_event(url, r, aggregation_key)
                status = AgentCheck.CRITICAL
                msg = "Got %s when hitting %s" % (r.status_code, url)
                self.warning(msg)
        except requests.exceptions.Timeout as e:
            # If there's a timeout
            self.timeout_event(url, timeout, aggregation_key)
            msg = "Timeout when hitting %s" % url
            status = AgentCheck.CRITICAL
            self.warning(msg)
        except Exception as e:
            msg = e.message
            status = AgentCheck.CRITICAL
        finally:
            self.service_check(self.check_name, status, tags=tags, message=msg)
            if status is AgentCheck.CRITICAL:
                raise Exception(msg)


        # Condition for request v1.x backward compatibility
        if hasattr(r.json, '__call__'):
            return r.json()
        else:
            return r.json

    def get_v2_app_versions(self, url, app, timeout):
        # Use a hash of the URL as an aggregation key
        aggregation_key = md5(url).hexdigest()

        tags = ['url:%s' % url, 'app_id:%s' % app['id'], 'version:%s' % app['version']]

        try:
            r = requests.get(url + "/v2/apps/" + app_id + "/versions", timeout=timeout)
            status = AgentCheck.OK
            if r.status_code != 200:
                self.status_code_event(url, r, aggregation_key)
                status = AgentCheck.CRITICAL
                msg = "Got %s when hitting %s" % (r.status_code, url)
                self.warning(msg)
        except requests.exceptions.Timeout as e:
            # If there's a timeout
            msg = "Timeout when hitting %s" % url
            self.timeout_event(url, timeout, aggregation_key)
            status = AgentCheck.CRITICAL
            self.warning(msg)
        except Exception as e:
            msg = e.message
            status = AgentCheck.CRITICAL
        finally:
            self.service_check(self.check_name, status, tags=tags, message=msg)
            if status is AgentCheck.CRITICAL:
                return None



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
