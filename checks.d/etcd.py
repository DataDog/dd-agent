# project
from checks import AgentCheck
from util import headers

# 3rd party
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
        'sendBandwidthRate': 'etcd.self.send.bandwidthrate',
        'recvPkgRate': 'etcd.self.recv.pkgrate',
        'recvBandwidthRate': 'etcd.self.recv.bandwidthrate'
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
        # Append the instance's URL in case there are more than one, that
        # way they can tell the difference!
        instance_tags.append("url:{0}".format(url))
        timeout = float(instance.get('timeout', self.DEFAULT_TIMEOUT))

        self_response = self.get_self_metrics(url, timeout)
        if self_response is not None:
            if self_response['state'] == 'StateLeader':
                instance_tags.append('etcd_state:leader')
            else:
                instance_tags.append('etcd_state:follower')

            for key in self.SELF_RATES:
                if key in self_response:
                    self.rate(self.SELF_RATES[key], self_response[key], tags=instance_tags)
                else:
                    self.log.warn("Missing key {0} in stats.".format(key))

            for key in self.SELF_GAUGES:
                if key in self_response:
                    self.gauge(self.SELF_GAUGES[key], self_response[key], tags=instance_tags)
                else:
                    self.log.warn("Missing key {0} in stats.".format(key))

        store_response = self.get_store_metrics(url, timeout)
        if store_response is not None:
            for key in self.STORE_RATES:
                if key in store_response:
                    self.rate(self.STORE_RATES[key], store_response[key], tags=instance_tags)
                else:
                    self.log.warn("Missing key {0} in stats.".format(key))

            for key in self.STORE_GAUGES:
                if key in store_response:
                    self.gauge(self.STORE_GAUGES[key], store_response[key], tags=instance_tags)
                else:
                    self.log.warn("Missing key {0} in stats.".format(key))

        if self_response is not None and store_response is not None:
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.OK, tags=instance_tags)

    def get_self_metrics(self, url, timeout):
        return self.get_json(url + "/v2/stats/self", timeout)

    def get_store_metrics(self, url, timeout):
        return self.get_json(url + "/v2/stats/store", timeout)

    def get_json(self, url, timeout):
        try:
            r = requests.get(url, timeout=timeout, headers=headers(self.agentConfig))
        except requests.exceptions.Timeout as e:
            # If there's a timeout
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL,
                message="Timeout when hitting %s" % url,
                tags = ["url:{0}".format(url)])
            raise

        if r.status_code != 200:
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL,
                message="Got %s when hitting %s" % (r.status_code, url),
                tags = ["url:{0}".format(url)])
            raise Exception("Http status code {0} on url {1}".format(r.status_code, url))

        return r.json()
