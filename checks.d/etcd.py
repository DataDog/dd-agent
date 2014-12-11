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

    DEFAULT_TIMEOUT = 5

    SERVICE_CHECK_NAME = 'etcd.can_connect'

    STORE_RATES = {
        'getsSuccess': 'etcd.store.gets.success',
        'getsFail': 'etcd.store.gets.fail',
        'setsSuccess': 'etcd.store.sets.success',
        'setsFail': 'etcd.store.sets.fail',
        'deleteSuccess': 'etcd.store.delete.success',
        'deleteFail': 'etcd.store.delete.fail',
        'updateSuccess': 'etcd.store.update.success',
        'updateFail': 'etcd.store.update.fail',
        'createSuccess': 'etcd.store.create.success',
        'createFail': 'etcd.store.create.fail',
        'compareAndSwapSuccess': 'etcd.store.compareandswap.success',
        'compareAndSwapFail': 'etcd.store.compareandswap.fail',
        'compareAndDeleteSuccess': 'etcd.store.compareanddelete.success',
        'compareAndDeleteFail': 'etcd.store.compareanddelete.fail',
        'expireCount': 'etcd.store.expire.count'
    }

    STORE_GAUGES = {
        'watchers': 'etcd.store.watchers'
    }

    SELF_GAUGES = {
        'sendPkgRate': 'etcd.self.send.pkgrate',
        'sendBandwidthRate': 'etcd.self.send.bandwidthrate'
    }

    SELF_RATES = {
        'recvAppendRequestCnt': 'etcd.self.recv.appendrequest.count',
        'sendAppendRequestCnt': 'etcd.self.send.appendrequest.count'
    }

    def check(self, instance):
        if 'url' not in instance:
            raise Exception('etcd instance missing "url" value.')

        # Load values from the instance config
        url = instance['url']
        instance_tags = instance.get('tags', [])
        timeout = float(instance.get('timeout', DEFAULT_TIMEOUT))

        storeResponse = self.get_store_metrics(url, timeout)
        if storeResponse is not None:
            for key, metric_name in self.STORE_RATES:
                self.rate(metric_name, storeResponse[key], tags=instance_tags)

            for key, metric_name in self.STORE_GAUGES:
                self.gauge(metric_name, storeResponse[key], tags=instance_tags)

        selfResponse = self.get_self_metrics(url, timeout)
        if selfResponse is not None:
            if selfResponse['state'] == 'leader':
                self.gauge('etcd.self.leader', 1, tags=instance_tags)
            else:
                self.gauge('etcd.self.leader', 0, tags=instance_tags)

            for key, metric_name in self.SELF_RATES:
                self.rate(metric_name, selfResponse[key], tags=instance_tags)

            for key, metric_name in self.SELF_GAUGES:
                self.gauge(metric_name, selfResponse[key], tags=instance_tags)

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
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL,
                message="Timeout when hitting %s" % url)
            return None

        if r.status_code != 200:
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL,
                message="Got %s when hitting %s" % (r.status_code, url))

        return r.json
