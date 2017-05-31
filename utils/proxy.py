# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import logging
import os
from urllib import getproxies
from urlparse import urlparse

log = logging.getLogger(__name__)

def get_no_proxy_from_env():
    return os.environ.get('no_proxy', os.environ.get('NO_PROXY', None))


def set_no_proxy_settings():
    """
    Starting with Agent 5.0.0, there should always be a local forwarder
    running and all payloads should go through it. So we should make sure
    that we pass the no_proxy environment variable that will be used by requests
    See: https://github.com/kennethreitz/requests/pull/945
    """
    to_add = ["127.0.0.1", "localhost", "169.254.169.254"]
    no_proxy = get_no_proxy_from_env()

    if no_proxy is None or not no_proxy.strip():
        no_proxy = []
    else:
        no_proxy = no_proxy.split(',')

    for host in to_add:
        if host not in no_proxy:
            no_proxy.append(host)

    os.environ['no_proxy'] = ','.join(no_proxy)


def get_proxy(agentConfig):
    proxy_settings = {}

    # First we read the proxy configuration from datadog.conf
    proxy_host = agentConfig.get('proxy_host')
    if proxy_host is not None:
        proxy_settings['host'] = proxy_host
        try:
            proxy_settings['port'] = int(agentConfig.get('proxy_port', 3128))
        except ValueError:
            log.error('Proxy port must be an Integer. Defaulting it to 3128')
            proxy_settings['port'] = 3128

        proxy_settings['user'] = agentConfig.get('proxy_user')
        proxy_settings['password'] = agentConfig.get('proxy_password')
        log.debug("Proxy Settings: %s:*****@%s:%s", proxy_settings['user'],
                  proxy_settings['host'], proxy_settings['port'])
        return proxy_settings

    # If no proxy configuration was specified in datadog.conf
    # We try to read it from the system settings
    try:
        proxy = getproxies().get('https')
        if proxy is not None:
            parse = urlparse(proxy)
            proxy_settings['host'] = parse.hostname
            proxy_settings['port'] = int(parse.port)
            proxy_settings['user'] = parse.username
            proxy_settings['password'] = parse.password

            log.debug("Proxy Settings: %s:*****@%s:%s", proxy_settings['user'],
                      proxy_settings['host'], proxy_settings['port'])
            return proxy_settings

    except Exception as e:
        log.debug("Error while trying to fetch proxy settings using urllib %s."
                  "Proxy is probably not set", str(e))

    return None


def config_proxy_skip(proxies, uri, skip_proxy=False):
    """
    Returns an amended copy of the proxies dictionary - used by `requests`,
    it will disable the proxy if the uri provided is to be reached directly.

    Keyword Arguments:
        proxies -- dict with existing proxies: 'https', 'http', 'no' as pontential keys
        uri -- uri to determine if proxy is necessary or not.
        skip_proxy -- if True, the proxy dictionary returned will disable all proxies
    """
    parsed_uri = urlparse(uri)

    # disable proxy if necessary
    if skip_proxy:
        if 'http' in proxies:
            proxies.pop('http')
        if 'https' in proxies:
            proxies.pop('https')
    elif proxies.get('no'):
        for url in proxies['no'].replace(';', ',').split(","):
            if url in parsed_uri.netloc:
                if 'http' in proxies:
                    proxies.pop('http')
                if 'https' in proxies:
                    proxies.pop('https')

    return proxies
