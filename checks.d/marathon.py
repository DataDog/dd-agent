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
    ACS_TOKEN = None

    APP_METRICS = [
        'backoffFactor',
        'backoffSeconds',
        'cpus',
        'disk',
        'instances',
        'mem',
        'taskRateLimit',
        'tasksRunning',
        'tasksStaged',
        'tasksHealthy',
        'tasksUnhealthy'
    ]

    def check(self, instance):
        if 'url' not in instance:
            raise Exception('Marathon instance missing "url" value.')

        # Load values from the instance config
        url = instance['url']
        user = instance.get('user')
        password = instance.get('password')
        acs_url = instance.get('acs_url')
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
        response = self.get_json(marathon_path, timeout, auth, acs_url, ssl_verify)
        if response is not None:
            self.gauge('marathon.apps', len(response['apps']), tags=instance_tags)
            for app in response['apps']:
                tags = ['app_id:' + app['id'], 'version:' + app['version']] + instance_tags
                for attr in self.APP_METRICS:
                    if attr in app:
                        self.gauge('marathon.' + attr, app[attr], tags=tags)

        # Number of running/pending deployments
        response = self.get_json(urljoin(url, "v2/deployments"), timeout, auth, acs_url, ssl_verify)
        if response is not None:
            self.gauge('marathon.deployments', len(response), tags=instance_tags)

    def refresh_acs_token(self, auth, acs_url):
        try:
            auth_body = {
                'uid': auth[0],
                'password': auth[1]
            }
            r = requests.post(urljoin(acs_url, "acs/api/v1/auth/login"), json=auth_body, verify=False)
            r.raise_for_status()
            token = r.json()['token']
            self.ACS_TOKEN = token
            return token
        except requests.exceptions.HTTPError:
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL,
                               message='acs auth url %s returned a status of %s' % (acs_url, r.status_code),
                               tags = ["url:{0}".format(acs_url)])
            raise Exception("Got %s when hitting %s" % (r.status_code, acs_url))

    def get_json(self, url, timeout, auth, acs_url, verify):
        params = {
            'timeout': timeout,
            'headers': {},
            'auth': auth,
            'verify': verify
        }
        if acs_url:
            # If the ACS token has not been set, go get it
            if not self.ACS_TOKEN:
                self.refresh_acs_token(auth, acs_url)
            params['headers']['authorization'] = 'token=%s' % self.ACS_TOKEN
            del params['auth']

        try:
            r = requests.get(url, **params)
            # If got unauthorized and using acs auth, refresh the token and try again
            if r.status_code == 401 and acs_url:
                self.refresh_acs_token(auth, acs_url)
                r = requests.get(url, **params)
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
                               tags = ["url:{0}".format(url)])

        return r.json()
