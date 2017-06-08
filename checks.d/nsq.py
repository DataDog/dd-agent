# stdlib
import time
from urlparse import urljoin

# 3rd party
import requests

# project
from checks import AgentCheck

class NSQ(AgentCheck):

    DEFAULT_TIMEOUT = 5
    CONNECT_CHECK_NAME = 'nsq.can_connect'
    HEALTH_CHECK_NAME = 'nsq.healthy'

    TOPIC_GAUGES = [
        'depth',
        'backend_depth' # Depth on disk as opposed to in memory
    ]
    TOPIC_COUNTS = [
        'message_count'
    ]

    CHANNEL_GAUGES = [
        'depth',
        'backend_depth',
        'in_flight_count',
        'deferred_count',
    ]
    CHANNEL_COUNTS = [
        'message_count',
        'requeue_count',
        'timeout_count'
    ]

    CLIENT_GAUGES = [
        'ready_count',
        'in_flight_count',
        'finish_count'
    ]
    CLIENT_COUNTS = [
        'message_count',
        'requeue_count'
    ]

    def check(self, instance):
        if 'url' not in instance:
            raise Exception('NSQ instance missing "url" value.')

        # Load values from the instance config
        url = instance['url']
        instance_tags = instance.get('tags', [])
        default_timeout = self.init_config.get('default_timeout', self.DEFAULT_TIMEOUT)
        timeout = float(instance.get('timeout', default_timeout))

        response = self.get_json(urljoin(url, "/stats?format=json"), timeout)
        if response is not None:
            health = response['data']['health']
            if health == 'OK':
                self.service_check(self.HEALTH_CHECK_NAME, AgentCheck.OK,
                    tags = ["url:{0}".format(url)]
                )
            else:
                self.service_check(self.HEALTH_CHECK_NAME, AgentCheck.CRITICAL,
                    message='%s returned a health of %s' % (url, health),
                    tags = ["url:{0}".format(url)]
                )


            self.gauge('nsq.topic_count', len(response['data']['topics']), tags=instance_tags)


            # Descend in to topic
            for topic in response['data']['topics']:
                self.gauge('nsq.topic.channel_count', len(topic['channels']), instance_tags)

                topic_tags = ['topic_name:' + topic['topic_name']] + instance_tags
                for attr in self.TOPIC_GAUGES:
                    self.gauge('nsq.topic.' + attr, topic[attr], tags=topic_tags)
                for attr in self.TOPIC_COUNTS:
                    self.monotonic_count('nsq.topic.' + attr, topic[attr], tags=topic_tags)


                # Descend in to channels
                for channel in topic['channels']:
                    channel_tags = ['channel_name:' + channel['channel_name']] + topic_tags

                    for attr in self.CHANNEL_GAUGES:
                        self.gauge('nsq.topic.channel.' + attr, channel[attr], tags=channel_tags)
                    for attr in self.CHANNEL_COUNTS:
                        self.monotonic_count('nsq.topic.channel.' + attr, channel[attr], tags=channel_tags)

                    # Descend in to clients
                    self.gauge('nsq.topic.channel.client_count', len(channel['clients']), tags=channel_tags)
                    for client in channel['clients']:
                        client_tags = [
                            'client_id:' + client['client_id'],
                            'client_version:' + client['version'],
                            'tls:' + str(client['tls']),
                            'user_agent:' + client['user_agent'],
                            'deflate:' + str(client['deflate']),
                            'snappy:' + str(client['snappy'])
                        ] + channel_tags
                        for attr in self.CLIENT_GAUGES:
                            self.gauge('nsq.topic.channel.client.' + attr, client[attr], tags=client_tags)
                        for attr in self.CLIENT_COUNTS:
                            self.monotonic_count('nsq.topic.channel.client.' + attr, client[attr], tags=client_tags)

                    for latency in channel['e2e_processing_latency']['percentiles']:
                        # NSQ does not zero pad the quantile's numberic representation,
                        # so we'll do that by splitting on the . and left-justifying up to
                        # 2 spaces, filling with 0. Note that `ljust` returns the whole strong
                        # if it is >= the length. This converts 0.5 in to '50' and .9999 in to '9999'
                        quantile = str(latency['quantile']).split(".")[1].ljust(2, "0")
                        self.gauge('nsq.topic.channel.e2e_processing_latency.p' + quantile, latency['value'], tags=channel_tags)

    def get_json(self, url, timeout):
        try:
            start_time = time.time()
            r = requests.get(url, timeout=timeout)
            r.raise_for_status()
            elapsed_time = time.time() - start_time
            self.histogram('nsq.stats_fetch_duration_seconds', int(elapsed_time))
        except requests.exceptions.Timeout:
            # If there's a timeout
            self.service_check(self.CONNECT_CHECK_NAME, AgentCheck.CRITICAL,
                message='%s timed out after %s seconds.' % (url, timeout),
                tags = ["url:{0}".format(url)])
            raise Exception("Timeout when hitting %s" % url)

        except requests.exceptions.HTTPError:
            self.service_check(self.CONNECT_CHECK_NAME, AgentCheck.CRITICAL,
                message='%s returned a status of %s' % (url, r.status_code),
                tags = ["url:{0}".format(url)])
            raise Exception("Got %s when hitting %s" % (r.status_code, url))

        else:
            self.service_check(self.CONNECT_CHECK_NAME, AgentCheck.OK,
                tags = ["url:{0}".format(url)]
            )

        return r.json()
