# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
from collections import defaultdict

# 3p
from kafka import KafkaClient
from kafka.common import OffsetRequestPayload as OffsetRequest
from kazoo.client import KazooClient
from kazoo.exceptions import NoNodeError

# project
from checks import AgentCheck

DEFAULT_KAFKA_TIMEOUT = 5
DEFAULT_ZK_TIMEOUT = 5


class KafkaCheck(AgentCheck):

    SOURCE_TYPE_NAME = 'kafka'

    def __init__(self, name, init_config, agentConfig, instances=None):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances=instances)
        self.zk_timeout = int(
            init_config.get('zk_timeout', DEFAULT_ZK_TIMEOUT))
        self.kafka_timeout = int(
            init_config.get('kafka_timeout', DEFAULT_KAFKA_TIMEOUT))

    def _get_all_consumers_offsets(self, zk_conn, zk_prefix):
        consumer_offsets = {}
        topics = defaultdict(set)
        consumers_zk_path = zk_prefix + '/consumers/'
        for consumer_group in self._try_get_children(zk_conn, consumers_zk_path):
            consumer_offsets_path = consumers_zk_path + consumer_group + '/offsets'
            for topic in self._try_get_children(zk_conn, consumer_offsets_path):
                consumer_topics_path = consumer_offsets_path + '/' + topic
                partitions = self._try_get_children(zk_conn, consumer_topics_path)
                topics[topic.encode('unicode_escape')].update(set([int(x) for x in partitions]))

                for partition in partitions:
                    try:
                       consumer_offset = int(zk_conn.get(consumer_topics_path + '/' + partition)[0])
                       key = (consumer_group.decode('unicode_escape'), topic.decode('unicode_escape'), int(partition))
                       consumer_offsets[key] = int(consumer_offset)
                    except NoNodeError:
                           self.log.warn('Could not read consumer offset from %s' % consumer_topics_path + '/' + partition)
        return topics, consumer_offsets

    def _try_get_children(self, zk_conn, zk_path):
        try:
           return zk_conn.get_children(zk_path)
        except NoNodeError:
           self.log.warn('No zookeeper node at %s' % zk_path)
           return []

    def _get_consumers_offsets_by_config(self,consumer_groups, zk_conn, zk_path_tmpl):
        consumer_offsets = {}
        topics = defaultdict(set)
        for consumer_group, topic_partitions in consumer_groups.iteritems():
            for topic, partitions in topic_partitions.iteritems():
                # Remember the topic partitions that we've see so that we can
                # look up their broker offsets later
                topics[topic].update(set(partitions))
                for partition in partitions:
                    zk_path = zk_path_tmpl % (consumer_group, topic, partition)
                    try:
                       consumer_offset = int(zk_conn.get(zk_path)[0])
                       key = (consumer_group, topic, partition)
                       consumer_offsets[key] = consumer_offset
                    except NoNodeError:
                       self.log.warn('No zookeeper node at %s' % zk_path)
                    except Exception:
                       self.log.exception('Could not read consumer offset from %s' % zk_path)
        return topics, consumer_offsets

    def check(self, instance):
        consumer_groups = self.read_config(instance, 'consumer_groups',
                                           cast=self._validate_consumer_groups)
        zk_connect_str = self.read_config(instance, 'zk_connect_str')
        kafka_host_ports = self.read_config(instance, 'kafka_connect_str')

        # Construct the Zookeeper path pattern
        zk_prefix = instance.get('zk_prefix', '')
        zk_path_tmpl = zk_prefix + '/consumers/%s/offsets/%s/%s'

        # Connect to Zookeeper
        zk_conn = KazooClient(zk_connect_str, timeout=self.zk_timeout)
        zk_conn.start()

        try:
            # Query Zookeeper for consumer offsets
            if 'none' in consumer_groups:
                topics, consumer_offsets = self._get_all_consumers_offsets(zk_conn, zk_prefix)
            else:
                topics, consumer_offsets = self._get_consumers_offsets_by_config(consumer_groups, zk_conn, zk_path_tmpl)
        finally:
            try:
                zk_conn.stop()
                zk_conn.close()
            except Exception:
                self.log.exception('Error cleaning up Zookeeper connection')

        # Connect to Kafka
        kafka_conn = KafkaClient(kafka_host_ports, timeout=self.kafka_timeout)

        try:
            # Query Kafka for the broker offsets
            broker_offsets = {}
            for topic, partitions in topics.items():
                offset_responses = kafka_conn.send_offset_request([
                    OffsetRequest(topic, p, -1, 1) for p in partitions])
                for resp in offset_responses:
                    broker_offsets[(resp.topic, resp.partition)] = resp.offsets[0]
        finally:
            try:
                kafka_conn.close()
            except Exception:
                self.log.exception('Error cleaning up Kafka connection')

        # Report the broker data
        for (topic, partition), broker_offset in broker_offsets.items():
            broker_tags = ['topic:%s' % topic, 'partition:%s' % partition]
            broker_offset = broker_offsets.get((topic, partition))
            self.gauge('kafka.broker_offset', broker_offset, tags=broker_tags)

        # Report the consumer
        for (consumer_group, topic, partition), consumer_offset in consumer_offsets.items():

            # Get the broker offset
            broker_offset = broker_offsets.get((topic, partition))

            # Report the consumer offset and lag
            tags = ['topic:%s' % topic, 'partition:%s' % partition,
                    'consumer_group:%s' % consumer_group]
            self.gauge('kafka.consumer_offset', consumer_offset, tags=tags)
            self.gauge('kafka.consumer_lag', broker_offset - consumer_offset,
                       tags=tags)

    # Private config validation/marshalling functions

    def _validate_consumer_groups(self, val):
        try:
            consumer_group, topic_partitions = val.items()[0]
            assert isinstance(consumer_group, (str, unicode))
            topic, partitions = topic_partitions.items()[0]
            assert isinstance(topic, (str, unicode))
            assert isinstance(partitions, (list, tuple))
            return val
        except Exception as e:
            self.log.exception(e)
            raise Exception('''The `consumer_groups` value must be a mapping of mappings, like this:
consumer_groups:
  myconsumer0: # consumer group name
    mytopic0: [0, 1] # topic: list of partitions
  myconsumer1:
    mytopic0: [0, 1, 2]
    mytopic1: [10, 12]
''')
