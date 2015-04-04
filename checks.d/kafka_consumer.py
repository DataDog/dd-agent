"""
Check offset, lag for consumer_groups per topic/partitions in zookeeper and kafka

You can ether specify witch consumer_groups, topcs partitions or ask zookeeper for
all.

"""

# stdlib
from collections import defaultdict

# project
from checks import AgentCheck

# 3rd party
from kafka.client import KafkaClient
from kafka.common import OffsetRequest
from kazoo.client import KazooClient
from kazoo.exceptions import NoNodeError

class KafkaCheck(AgentCheck):

    SOURCE_TYPE_NAME = 'kafka'


    def _get_offsets_from_zk(self, zk_conn, zk_prefix):
        """
        Ask zookeeper for all consumer_groups setup.
        """
        consumer_offsets = {}
        topics = defaultdict(set)

        zk_path_consumer = zk_prefix + '/consumers/'
        zk_path_topic_tmpl = zk_path_consumer + '%s/offsets/'
        zk_path_partition_tmpl = zk_path_topic_tmpl + '%s/'
        zk_path_offset_tmpl = zk_path_partition_tmpl + '%s'
        try:
            for consumer_group in zk_conn.get_children(zk_path_consumer):

                zk_path_topic = zk_path_topic_tmpl % (consumer_group)
                for topic in zk_conn.get_children(zk_path_topic):

                    zk_path_partition = zk_path_partition_tmpl % (consumer_group, topic)
                    partitions = []
                    for partition in zk_conn.get_children(zk_path_partition):
                        partitions.append(int(partition))
                        zk_path_offset = zk_path_offset_tmpl % (consumer_group, topic, partition)
                        consumer_offset = int(zk_conn.get(zk_path_offset)[0])
                        key = (consumer_group, topic, int(partition))
                        consumer_offsets[key] = consumer_offset
                    topics[str(topic)].update(set(partitions))

        except NoNodeError:
            self.log.warn('No zookeeper node please check zk_prefix')
        except Exception:
            self.log.exception('Could not read consumer offset')

        return (consumer_offsets, topics)


    def _get_offsets_based_on_config(self, zk_conn, zk_prefix, consumer_groups):
        """
        Base the check on what is in the configuration.
        """

        zk_path_tmpl = zk_prefix + '/consumers/%s/offsets/%s/%s'

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

        return (consumer_offsets, topics)


    def check(self, instance):
        """
        Check offset in kafka for consumer_groups,topics and partitions.


        Alt 1;
        You can ether specify consumer_groups, topics and partitions in
        config file like

        consumer_groups:
            my_consumer:
              my_topic: [0, 1, 4, 12]

        Alt 2;
        Ask zookeeper for the current configuration and use that, it will
        do this if no consumer_groups is specifyed in configuration.

        """

        zk_connect_str = self.read_config(instance, 'zk_connect_str')
        kafka_host_ports = self.read_config(instance, 'kafka_connect_str')

        # Construct the Zookeeper path pattern
        zk_prefix = instance.get('zk_prefix', '')
        # Connect to Zookeeper
        zk_conn = KazooClient(zk_connect_str)
        zk_conn.start()


        try:
            if instance.has_key('consumer_groups'):
                #Alt1, Only check the given consumer groups, topics and partions.
                consumer_groups = self.read_config(instance, 'consumer_groups',
                                                   cast=self._validate_consumer_groups)

                (consumer_offsets, topics) = \
                    self._get_offsets_based_on_config(zk_conn, zk_prefix, consumer_groups)
            else:
                #Alt2, Non given lets ask zookeeper for a full set.
                (consumer_offsets, topics) = \
                    self._get_offsets_from_zk(zk_conn, zk_prefix)

        finally:
            try:
                zk_conn.stop()
                zk_conn.close()
            except Exception:
                self.log.exception('Error cleaning up Zookeeper connection')

        # Connect to Kafka
        kafka_conn = KafkaClient(kafka_host_ports)

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
        except Exception, e:
            self.log.exception(e)
            raise Exception('''The `consumer_groups` value must be a mapping of mappings, like this:
consumer_groups:
  myconsumer0: # consumer group name
    mytopic0: [0, 1] # topic: list of partitions
  myconsumer1:
    mytopic0: [0, 1, 2]
    mytopic1: [10, 12]
''')

