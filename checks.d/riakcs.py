# (C) Datadog, Inc. 2010-2016
# (C) Jon Glick <jglick@basho.com> 2014
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
from collections import defaultdict

# 3rd party
from boto.s3.connection import S3Connection
import simplejson as json

# project
from checks import AgentCheck
from config import _is_affirmative


def multidict(ordered_pairs):
    """Convert duplicate keys values to lists."""
    # read all values into lists
    d = defaultdict(list)
    for k, v in ordered_pairs:
        d[k].append(v)
    # unpack lists that have only 1 item
    for k, v in d.items():
        if len(v) == 1:
            d[k] = v[0]
    return dict(d)


class RiakCs(AgentCheck):

    STATS_BUCKET = 'riak-cs'
    STATS_KEY = 'stats'
    SERVICE_CHECK_NAME = 'riakcs.can_connect'

    def check(self, instance):
        s3, aggregation_key, tags, metrics = self._connect(instance)

        stats = self._get_stats(s3, aggregation_key)

        self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.OK,
          tags=["aggregation_key:{0}".format(aggregation_key)])

        self.process_stats(stats, tags, metrics)

    def process_stats(self, stats, tags, metrics):
        if not stats:
            raise Exception("No stats were collected")

        if "legend" not in stats:
            # riak cs 2.1+ stats format
            if metrics:
                metrics = set(metrics)
                metrics.update(V21_DEFAULT_METRICS)
            else:
                metrics = V21_DEFAULT_METRICS
            for key, value in stats.iteritems():
                if key not in metrics:
                    continue
                suffix = key.rsplit("_", 1)[-1]
                method = STATS_METHODS.get(suffix, "gauge")
                getattr(self, method)("riakcs.{}".format(key), value, tags=tags)
        else:
            # pre 2.1 stats format
            legends = dict([(len(k), k) for k in stats["legend"]])
            del stats["legend"]
            for key, values in stats.iteritems():
                legend = legends[len(values)]
                for i, value in enumerate(values):
                    metric_name = "riakcs.{0}.{1}".format(key, legend[i])
                    self.gauge(metric_name, value, tags=tags)

    def _connect(self, instance):
        for e in ("access_id", "access_secret"):
            if e not in instance:
                raise Exception("{0} parameter is required.".format(e))

        s3_settings = {
            "aws_access_key_id": instance.get('access_id', None),
            "aws_secret_access_key": instance.get('access_secret', None),
            "proxy": instance.get('host', 'localhost'),
            "proxy_port": int(instance.get('port', 8080)),
            "is_secure": _is_affirmative(instance.get('is_secure', True))
        }

        if instance.get('s3_root'):
            s3_settings['host'] = instance['s3_root']

        aggregation_key = s3_settings['proxy'] + ":" + str(s3_settings['proxy_port'])

        try:
            s3 = S3Connection(**s3_settings)
        except Exception as e:
            self.log.error("Error connecting to {0}: {1}".format(aggregation_key, e))
            self.service_check(
                self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL,
                tags=["aggregation_key:{0}".format(aggregation_key)],
                message=str(e))
            raise

        tags = instance.get("tags", [])
        tags.append("aggregation_key:{0}".format(aggregation_key))

        metrics = instance.get("metrics", [])

        return s3, aggregation_key, tags, metrics

    def _get_stats(self, s3, aggregation_key):
        try:
            bucket = s3.get_bucket(self.STATS_BUCKET, validate=False)
            key = bucket.get_key(self.STATS_KEY)
            stats_str = key.get_contents_as_string()
            stats = self.load_json(stats_str)

        except Exception as e:
            self.log.error("Error retrieving stats from {0}: {1}".format(aggregation_key, e))
            self.service_check(
                self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL,
                tags=["aggregation_key:{0}".format(aggregation_key)],
                message=str(e))
            raise

        return stats

    @classmethod
    def load_json(cls, text):
        data = json.loads(text)
        if "legend" in data:
            # riak cs before v2.1 had duplicate keys
            data = json.JSONDecoder(object_pairs_hook=multidict).decode(text)
        return data


STATS_METHODS = {
    "one": "count",
}

# This list includes most S3 API metrics as well as memory stats. Some
# have been excluded, mainly just to keep size of the default set of
# metrics somewhat reasonable.
#
# Excluded S3 metrics:
#   - bucket_acl_(get|put)
#   - object_acl_(get|put)
#   - bucket_policy_(get|put|delete)
#   - *_in_(one|total)
#   - *_time_error_*
#   - *_time_100
#
# Any of these excluded metrics in addition to many others (there are
# over 1000 to choose from) can be added by specifying them in the
# riakcs.yaml config file under the "metrics" key in the instance
# config; the value should be a list of metric names.
#
# Helpful references:
# - https://github.com/basho/riak_cs/wiki/Riak-cs-and-stanchion-metrics

V21_DEFAULT_METRICS = set([
    "memory_atom",
    "memory_atom_used",
    "memory_binary",
    "memory_code",
    "memory_ets",
    "memory_processes",
    "memory_processes_used",
    "memory_system",
    "memory_total",
    "service_get_out_error_one",
    "service_get_out_error_total",
    "service_get_out_one",
    "service_get_out_total",
    "service_get_time_95",
    "service_get_time_99",
    "service_get_time_mean",
    "service_get_time_median",
    "bucket_delete_out_error_one",
    "bucket_delete_out_error_total",
    "bucket_delete_out_one",
    "bucket_delete_out_total",
    "bucket_delete_time_95",
    "bucket_delete_time_99",
    "bucket_delete_time_mean",
    "bucket_delete_time_median",
    "bucket_head_out_error_one",
    "bucket_head_out_error_total",
    "bucket_head_out_one",
    "bucket_head_out_total",
    "bucket_head_time_95",
    "bucket_head_time_99",
    "bucket_head_time_mean",
    "bucket_head_time_median",
    "bucket_put_out_error_one",
    "bucket_put_out_error_total",
    "bucket_put_out_one",
    "bucket_put_out_total",
    "bucket_put_time_95",
    "bucket_put_time_99",
    "bucket_put_time_mean",
    "bucket_put_time_median",
    "bucket_location_get_out_error_one",
    "bucket_location_get_out_error_total",
    "bucket_location_get_out_one",
    "bucket_location_get_out_total",
    "bucket_location_get_time_95",
    "bucket_location_get_time_99",
    "bucket_location_get_time_mean",
    "bucket_location_get_time_median",
    "list_uploads_get_out_error_one",
    "list_uploads_get_out_error_total",
    "list_uploads_get_out_one",
    "list_uploads_get_out_total",
    "list_uploads_get_time_95",
    "list_uploads_get_time_99",
    "list_uploads_get_time_mean",
    "list_uploads_get_time_median",
    "multiple_delete_post_out_error_one",
    "multiple_delete_post_out_error_total",
    "multiple_delete_post_out_one",
    "multiple_delete_post_out_total",
    "multiple_delete_post_time_95",
    "multiple_delete_post_time_99",
    "multiple_delete_post_time_mean",
    "multiple_delete_post_time_median",
    "list_objects_get_out_error_one",
    "list_objects_get_out_error_total",
    "list_objects_get_out_one",
    "list_objects_get_out_total",
    "list_objects_get_time_95",
    "list_objects_get_time_99",
    "list_objects_get_time_mean",
    "list_objects_get_time_median",
    "object_put_out_error_one",
    "object_put_out_error_total",
    "object_put_out_one",
    "object_put_out_total",
    "object_put_time_95",
    "object_put_time_99",
    "object_put_time_mean",
    "object_put_time_median",
    "object_delete_out_error_one",
    "object_delete_out_error_total",
    "object_delete_out_one",
    "object_delete_out_total",
    "object_delete_time_95",
    "object_delete_time_99",
    "object_delete_time_mean",
    "object_delete_time_median",
    "object_get_out_error_one",
    "object_get_out_error_total",
    "object_get_out_one",
    "object_get_out_total",
    "object_get_time_95",
    "object_get_time_99",
    "object_get_time_mean",
    "object_get_time_median",
    "object_head_out_error_one",
    "object_head_out_error_total",
    "object_head_out_one",
    "object_head_out_total",
    "object_head_time_95",
    "object_head_time_99",
    "object_head_time_mean",
    "object_head_time_median",
    "object_put_copy_out_error_one",
    "object_put_copy_out_error_total",
    "object_put_copy_out_one",
    "object_put_copy_out_total",
    "object_put_copy_time_95",
    "object_put_copy_time_99",
    "object_put_copy_time_mean",
    "object_put_copy_time_median",
    "multipart_post_out_error_one",
    "multipart_post_out_error_total",
    "multipart_post_out_one",
    "multipart_post_out_total",
    "multipart_post_time_95",
    "multipart_post_time_99",
    "multipart_post_time_mean",
    "multipart_post_time_median",
    "multipart_upload_delete_out_error_one",
    "multipart_upload_delete_out_error_total",
    "multipart_upload_delete_out_one",
    "multipart_upload_delete_out_total",
    "multipart_upload_delete_time_95",
    "multipart_upload_delete_time_99",
    "multipart_upload_delete_time_mean",
    "multipart_upload_delete_time_median",
    "multipart_upload_get_out_error_one",
    "multipart_upload_get_out_error_total",
    "multipart_upload_get_out_one",
    "multipart_upload_get_out_total",
    "multipart_upload_get_time_95",
    "multipart_upload_get_time_99",
    "multipart_upload_get_time_mean",
    "multipart_upload_get_time_median",
    "multipart_upload_post_out_error_one",
    "multipart_upload_post_out_error_total",
    "multipart_upload_post_out_one",
    "multipart_upload_post_out_total",
    "multipart_upload_post_time_95",
    "multipart_upload_post_time_99",
    "multipart_upload_post_time_mean",
    "multipart_upload_post_time_median",
    "multipart_upload_put_out_error_one",
    "multipart_upload_put_out_error_total",
    "multipart_upload_put_out_one",
    "multipart_upload_put_out_total",
    "multipart_upload_put_time_95",
    "multipart_upload_put_time_99",
    "multipart_upload_put_time_mean",
    "multipart_upload_put_time_median",
])
