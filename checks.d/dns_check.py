# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
import time

# 3p
import dns.resolver

# project
from checks import AgentCheck
from util import Platform


# These imports are necessary because otherwise dynamic type
# resolution will fail on windows without it.
# See more here: https://github.com/rthalley/dnspython/issues/39.
if Platform.is_win32():
    from dns.rdtypes.ANY import *  # noqa
    from dns.rdtypes.IN import *  # noqa


class DNSCheck(AgentCheck):
    SERVICE_CHECK_NAME = 'dns.can_resolve'
    DEFAULT_TIMEOUT = 5

    def __init__(self, name, init_config, agentConfig, instances=None):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances)
        self.default_timeout = init_config.get('default_timeout', self.DEFAULT_TIMEOUT)

    def check(self, instance):
        if 'hostname' not in instance:
            self.log.info("Skipping instance, no hostname found.")
            return

        timeout = float(instance.get('timeout', self.default_timeout))
        self.query_dns(instance, timeout)

    def query_dns(self, instance, timeout):
        """Perform the DNS query, and report its duration as a gauge"""
        start_time = end_time = 0.0
        resolver = dns.resolver.Resolver()
        resolver.lifetime = timeout

        hostname = instance.get('hostname')
        tags = self._get_tags(instance)

        # if a specific DNS server was defined use it, else use the system default
        nameserver = instance.get('nameserver')
        if nameserver is not None:
            resolver.nameservers = [nameserver]

        status = AgentCheck.CRITICAL
        start_time = time.time()
        try:
            self.log.debug('Resolving hostname %s...' % hostname)
            answer = resolver.query(hostname)
            assert(answer.rrset.items[0].address)
            end_time = time.time()
        except dns.exception.Timeout:
            self.log.error('DNS resolution of %s timed out' % hostname)
            self.service_check(self.SERVICE_CHECK_NAME, status, tags=self._get_tags(instance))
            raise
        except Exception:
            self.log.exception('DNS resolution of %s has failed.' % hostname)
            self.service_check(self.SERVICE_CHECK_NAME, status, tags=self._get_tags(instance))
            raise
        else:
            if end_time - start_time > 0:
                self.gauge('dns.response_time', end_time - start_time, tags=tags)
                self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.OK, tags=self._get_tags(instance))

    def _get_tags(self, instance):
        tags = []
        try:
            nameserver = instance.get('nameserver') or dns.resolver.Resolver().nameservers[0]
            tags.append('nameserver:%s' % nameserver)
        except IndexError:
            self.log.error('No DNS server was found on this host.')

        tags.append('resolved_hostname:%s' % instance.get('hostname'))
        return tags
