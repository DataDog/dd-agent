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

    keys = [
        "object_put_acl",
        "bucket_create",
        "bucket_list_keys",
        "service_get_buckets",
        "block_delete",
        "block_put",
        "block_get_retry",
        "block_get",
        "bucket_delete",
        "bucket_get_acl",
        "bucket_put_acl",
        "object_get",
        "object_put",
        "object_head",
        "object_delete",
        "object_get_acl"
    ]
    pool_keys = [
        "bucket_list_pool",
        "request_pool"
    ]

    def __init__(self, name, init_config, agentConfig, instances=None):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances)

    def check(self, instance):

      s3_settings=dict(
        aws_access_key_id=instance.get('access_id', None),
        aws_secret_access_key=instance.get('access_secret', None),
        port=instance.get('s3_port', None),
        proxy=instance.get('proxy_host', None),
        proxy_port=instance.get('proxy_port', None),
        proxy_user=instance.get('proxy_user', None),
        proxy_pass=instance.get('proxy_pass', None),
        is_secure=instance.get('is_secure', None))

      if instance.get('s3_host'):
        s3_settings['host'] = instance['s3_host']

      aggregation_key = md5(json.dumps(s3_settings)).hexdigest()

      default_timeout = self.init_config.get('default_timeout', 5)
      timeout         = float(instance.get('timeout', default_timeout))

      try:

        self.s3 = S3Connection(**s3_settings)
        stats_key = self.s3.get_bucket('riak-cs', validate=False).get_key('stats')
        stats_str = stats_key.get_contents_as_string()
        stats = json.loads(stats_str)

      except socket.timeout, e:
          self.timeout_event(timeout, aggregation_key)
          return

      except socket.error, e:
          self.timeout_event(timeout, aggregation_key)
          return

      except HttpLib2Error, e:
          self.timeout_event(timeout, aggregation_key)
          return

      except boto.exception, e:
          self.timeout_event(timeout, aggregation_key)
          return

      for key in self.keys:
        if key not in stats:
          continue
        vals = stats[key]
        self.count('riakcs.' + key, vals.pop(0))
        for gauge in [
          "rate", "latency_mean", "latency_median",
          "latency_95", "latency_99" ]:
          self.gauge('riakcs.' + key + "_" + gauge, vals.pop(0))

      self.gauge('riakcs.test', 1)

      for key in self.pool_keys:
        if key not in stats:
          continue
        vals = stats[key]
        for gauge in ["workers", "overflow", "size"]:
          self.gauge('riakcs.' + key + "_" + gauge, vals.pop(0))

    def timeout_event(self, timeout, aggregation_key):
        self.event({
            'timestamp': int(time.time()),
            'event_type': 'riak_check',
            'msg_title': 'riak check timeout',
            'msg_text': 'stats out after %s seconds.' % (timeout),
            'aggregation_key': aggregation_key
        })

    def status_code_event(self, r, aggregation_key):
        self.event({
            'timestamp': int(time.time()),
            'event_type': 'riak_check',
            'msg_title': 'Invalid reponse code for riak check',
            'msg_text': 'stats returned a status of %s' % (r.status_code),
            'aggregation_key': aggregation_key
        })
