# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

from fnmatch import fnmatchcase
import requests
from collections import defaultdict
from google.protobuf.internal.decoder import _DecodeVarint32  # pylint: disable=E0611,E0401
from utils.prometheus import metrics_pb2

from prometheus_client.parser import text_fd_to_metric_families
from datadog_checks.checks.prometheus.mixins import PrometheusFormat, UnknownFormatError
from datadog_checks.checks.prometheus.mixins import PrometheusScraperMixin as PrometheusScraper

from checks import AgentCheck
