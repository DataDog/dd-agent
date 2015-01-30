# stdlib
import time
from hashlib import md5
import socket

# project
from checks import AgentCheck

# 3rd party
import simplejson as json
from boto.s3.connection import S3Connection

class RiakCs(AgentCheck):

    STATS_BUCKET = 'riak-cs'
    STATS_KEY = 'stats'

    STAT_KEYS = [
        # Object Keys
        "object_get", "object_put", "object_delete", "object_head",
        "object_get_acl", "object_put_acl",
        # Bucket Keys
        "bucket_create", "service_get_buckets", "bucket_delete",
        "bucket_list_keys", "bucket_get_acl", "bucket_put_acl",
        # Block Keys
        "block_get", "block_put", "block_delete", "block_get_retry" ]
    STAT_GAUGES = [
        "rate", "latency_mean", "latency_median",
        "latency_95", "latency_99" ]
    POOL_KEYS = [
        "bucket_list_pool", "request_pool" ]
    POOL_GAUGES = [
        "workers", "overflow", "size" ]

    def check(self, instance):

      s3_settings=dict(
        aws_access_key_id=instance.get('access_id', None),
        aws_secret_access_key=instance.get('access_secret', None),
        proxy=instance.get('host','localhost'),
        proxy_port=instance.get('port', 8080),
        is_secure=instance.get('is_secure', None))

      if instance.get('s3_root'):
        s3_settings['host'] = instance['s3_root']

      aggregation_key = s3_settings['proxy'] + ":" + str(s3_settings['proxy_port'])

      s3 = self._connect(s3_settings, aggregation_key)

      stats = self._get_stats(s3, aggregation_key)

      if stats:

        for key in self.STAT_KEYS:
          if key not in stats:
            continue
          vals = stats[key]
          self.count('riakcs.' + key, vals.pop(0))
          for gauge in self.STAT_GAUGES:
            self.gauge('riakcs.' + key + "_" + gauge, vals.pop(0))

        for key in self.POOL_KEYS:
          if key not in stats:
            continue
          vals = stats[key]
          for gauge in self.POOL_GAUGES:
            self.gauge('riakcs.' + key + "_" + gauge, vals.pop(0))

    def _connect(self, s3_settings, aggregation_key):

      try:
        s3 = S3Connection(**s3_settings)

      except Exception, e:
          self._error("Error connecting to " + aggregation_key, e)
          return

      return s3

    def _get_stats(self, s3, aggregation_key):

      try:
          bucket = s3.get_bucket(self.STATS_BUCKET, validate=False)
          key = bucket.get_key(self.STATS_KEY)
          stats_str = key.get_contents_as_string()
          stats = json.loads(stats_str)

      except Exception, e:
          self._error("Error retrieving stats from " + aggregation_key, e)
          return

      return stats

    def _error(self, message, error):
        self.warning(message + ": " + str(error))
        self.log.critical(message + ": " + str(error))
