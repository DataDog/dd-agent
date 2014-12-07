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

class Etcd(AgentCheck):
    def check(self, instance):
        if 'url' not in instance:
            raise Exception('etcd instance missing "url" value.')

        # Load values from the instance config
        url = instance['url']
        instance_tags = instance.get('tags', [])
        default_timeout = self.init_config.get('default_timeout', 5)
        timeout = float(instance.get('timeout', default_timeout))

        tags = instance_tags

        storeResponse = self.get_store_metrics(url, timeout)
        if storeResponse is not None:
            for key in ['getsSuccess', 'getsFail', 'setsSuccess', 'setsFail', 'deleteSuccess', 'deleteFail', 'updateSuccess', 'updateFail', 'createSuccess', 'createFail', 'compareAndSwapSuccess', 'compareAndSwapFail', 'compareAndDeleteSuccess', 'compareAndDeleteFail', 'expireCount']:
                self.rate('etcd.store.' + key, storeResponse[key], tags=tags)

            for key in ['watchers']:
                self.gauge('etcd.store.' + key, storeResponse[key], tags=tags)

        selfResponse = self.get_self_metrics(url, timeout)
        if selfResponse is not None:
            if selfResponse['state'] == 'leader':
                self.gauge('etcd.self.leader', 1, tags=tags)
            else:
                self.gauge('etcd.self.leader', 0, tags=tags)

            for key in ['recvAppendRequestCnt', 'sendAppendRequestCnt']:
                self.rate('etcd.self.' + key, selfResponse[key], tags=tags)

            for key in ['sendPkgRate', 'sendBandwidthRate']:
                self.gauge('etcd.self.' + key, selfResponse[key], tags=tags)

    def get_self_metrics(self, url, timeout):
        return self.get_json(url + "/v2/stats/self", timeout)

    def get_store_metrics(self, url, timeout):
        return self.get_json(url + "/v2/stats/store", timeout)

    def get_json(self, url, timeout):
        # Use a hash of the URL as an aggregation key
        aggregation_key = md5(url).hexdigest()
        try:
            r = requests.get(url, timeout=timeout)
        except requests.exceptions.Timeout as e:
            # If there's a timeout
            self.timeout_event(url, timeout, aggregation_key)
            self.warning("Timeout when hitting %s" % url)
            return None

        if r.status_code != 200:
            self.status_code_event(url, r, aggregation_key)
            self.warning("Got %s when hitting %s" % (r.status_code, url))
            return None

        # Condition for request v1.x backward compatibility
        if hasattr(r.json, '__call__'):
            return r.json()
        else:
            return r.json


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
