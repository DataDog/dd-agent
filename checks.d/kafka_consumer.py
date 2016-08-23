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

    def _get_partitions_for_topic(self, zk_conn, zk_path_partition_tmpl, consumer_group, topic):
        """Returns all partitions for the topic as found in zookeeper"""
        zk_path = zk_path_partition_tmpl % (consumer_group, topic)
        return self._get_children(zk_conn, zk_path, 'partitions')

    def _get_children(self, zk_conn, zk_path, name_for_error):
        children = []
        try:
            children = zk_conn.get_children(zk_path)
        except NoNodeError:
            self.log.warn('No zookeeper node at %s' % zk_path)
        except:
            self.log.exception('Could not read %s from %s' % (name_for_error, zk_path))
        return children

    def check(self, instance):
        # Only validate consumer_groups if specified; fallback to zk otherwise
        if 'consumer_groups' in instance:
            consumer_groups = self.read_config(instance, 'consumer_groups',
                                               cast=self._validate_consumer_groups)
        zk_connect_str = self.read_config(instance, 'zk_connect_str')
        kafka_host_ports = self.read_config(instance, 'kafka_connect_str')

        # Construct the Zookeeper path pattern
        zk_prefix = instance.get('zk_prefix', '')
        zk_path_consumer = zk_prefix + '/consumers/'
        zk_path_topic_tmpl = zk_path_consumer + '%s/offsets/'
        zk_path_partition_tmpl = zk_path_topic_tmpl + '%s/'

        # Connect to Zookeeper
        zk_conn = KazooClient(zk_connect_str, timeout=self.zk_timeout)
        zk_conn.start()

        try:
            # Query Zookeeper for consumer offsets
            consumer_offsets = {}
            topics = defaultdict(set)
            if not consumer_groups:
                consumer_groups = {consumer_group: None
                                   for consumer_group in self._get_children(zk_conn,
                                                                            zk_path_consumer,
                                                                            'consumer groups')}
            for consumer_group, topic_partitions in consumer_groups.iteritems():
                if topic_partitions is None:
                    zk_path_topic = zk_path_topic_tmpl % (consumer_group)
                    topic_partitions = self._get_children(zk_conn,
                                                          zk_path_topic,
                                                          'topics')
                if isinstance(topic_partitions, list):
                    topics = topic_partitions
                    topic_partitions = {topic: self._get_partitions_for_topic(zk_conn,
                                                                              zk_path_partition_tmpl,
                                                                              consumer_group,
                                                                              topic)
                                        for topic in topics}
                for topic, partitions in topic_partitions.iteritems():
                    # Remember the topic partitions that we've see so that we can
                    # look up their broker offsets later
                    topics[topic].update(set(partitions))
                    for partition in partitions:
                        zk_path = zk_path_partition_tmpl % (consumer_group, topic, partition)
                        try:
                            consumer_offset = int(zk_conn.get(zk_path)[0])
                            key = (consumer_group, topic, partition)
                            consumer_offsets[key] = consumer_offset
                        except NoNodeError:
                            self.log.warn('No zookeeper node at %s' % zk_path)
                        except:
                            self.log.exception('Could not read consumer offset from %s' % zk_path)
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
            if isinstance(val, dict):
                consumer_group, topic_partitions = val.items()[0]
                assert isinstance(consumer_group, (str, unicode))
                # Allow just specifying the topic instead of all the partitions
                if isinstance(topic_partitions, dict):
                    topic, partitions = topic_partitions.items()[0]
                    assert isinstance(topic, (str, unicode))
                    assert isinstance(partitions, (list, tuple))
                else:
                    assert isinstance(topic_partitions, (list, tuple))
            else:
                assert isinstance(val, (list, tuple))
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
