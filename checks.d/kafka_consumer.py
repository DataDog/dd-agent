from collections import defaultdict
from checks import AgentCheck
from kafka.client import KafkaClient
from kafka.common import OffsetRequest
from kazoo.client import KazooClient
from kazoo.exceptions import NoNodeError
import random

class KafkaCheck(AgentCheck):
    def check(self, instance):
        consumer_groups = instance['consumer_groups']

        # Construct the Zookeeper path pattern
        zk_prefix = instance.get('zk_prefix', '')
        zk_path_tmpl = zk_prefix + '/consumers/%s/offsets/%s/%s'

        # Connect to Zookeeper
        zk_connect_str = instance['zk_connect_str']
        zk_conn = KazooClient(zk_connect_str)
        zk_conn.start()

        try:
            # Query Zookeeper for consumer offsets
            consumer_offsets = {}
            topics = defaultdict(set)
            for consumer_group, topic_partitions in consumer_groups.items():
                for topic, partitions in topic_partitions.items():
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
        finally:
            try:
                zk_conn.stop()
                zk_conn.close()
            except Exception:
                self.log.exception('Error cleaning up Zookeeper connection')

        # Connect to Kafka
        host_ports = [hp.strip().split(':') for hp
                      in instance['kafka_connect_str'].split(',')]
        kafka_host, kafka_port = random.choice(host_ports)
        kafka_conn = KafkaClient(kafka_host, int(kafka_port))

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
