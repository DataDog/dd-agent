# (C) Datadog, Inc. 2014-2016
# (C)  graemej <graeme.johnson@jadedpixel.com> 2014
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)


# stdlib
from urlparse import urljoin

# 3rd party
import requests

# project
from checks import AgentCheck
from config import _is_affirmative


class Marathon(AgentCheck):

    DEFAULT_TIMEOUT = 5
    SERVICE_CHECK_NAME = 'marathon.can_connect'

    APP_METRICS = [
        'backoffFactor',
        'backoffSeconds',
        'cpus',
        'disk',
        'instances',
        'mem',
        'taskRateLimit',
        'tasksRunning',
        'tasksStaged'
    ]

    def check(self, instance):
        if 'url' not in instance:
            raise Exception('Marathon instance missing "url" value.')

        # Load values from the instance config
        url = instance['url']
        user = instance.get('user')
        password = instance.get('password')
        if user is not None and password is not None:
            auth = (user,password)
        else:
            auth = None
        ssl_verify = not _is_affirmative(instance.get('disable_ssl_validation', False))
        group = instance.get('group', None)

        instance_tags = instance.get('tags', [])
        default_timeout = self.init_config.get('default_timeout', self.DEFAULT_TIMEOUT)
        timeout = float(instance.get('timeout', default_timeout))

        # Marathon apps
        if group is None:
            marathon_path = urljoin(url, "v2/apps")
        else:
            marathon_path = urljoin(url, "v2/groups/{}".format(group))
        response = self.get_json(marathon_path, timeout, auth, ssl_verify)
        if response is not None:
            self.gauge('marathon.apps', len(response['apps']), tags=instance_tags)
            for app in response['apps']:
                tags = ['app_id:' + app['id'], 'version:' + app['version']] + instance_tags
                for attr in self.APP_METRICS:
                    if attr in app:
                        self.gauge('marathon.' + attr, app[attr], tags=tags)

        # Number of running/pending deployments
        response = self.get_json(urljoin(url, "v2/deployments"), timeout, auth, ssl_verify)
        if response is not None:
            self.gauge('marathon.deployments', len(response), tags=instance_tags)

    def get_json(self, url, timeout, auth, verify):
        try:
            r = requests.get(url, timeout=timeout, auth=auth, verify=verify)
            r.raise_for_status()
        except requests.exceptions.Timeout:
            # If there's a timeout
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL,
                message='%s timed out after %s seconds.' % (url, timeout),
                tags = ["url:{0}".format(url)])
            raise Exception("Timeout when hitting %s" % url)

        except requests.exceptions.HTTPError:
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL,
                message='%s returned a status of %s' % (url, r.status_code),
                tags = ["url:{0}".format(url)])
            raise Exception("Got %s when hitting %s" % (r.status_code, url))

        except requests.exceptions.ConnectionError:
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL,
                message='%s Connection Refused.' % (url),
                tags = ["url:{0}".format(url)])
            raise Exception("Connection refused when hitting %s" % url)

        else:
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.OK,
                tags = ["url:{0}".format(url)]
            )

        return r.json()
