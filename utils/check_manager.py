# stdlib
import os

# 3p
import requests

# project

GITHUB_CONTENT = 'https://raw.githubusercontent.com'
GITHUB_SOURCE = 'https://github.com'

CHECKS_PATH = 'checks.e'

DEFAULT_VERSION = 'master'
REQUIRED_FILES = ['check.py', 'check.yaml.example', 'check.yaml.erb']


class CheckNotFound(Exception):
    pass


class CheckManager(object):
    """
    TODO
    """

    @classmethod
    def install(cls, check_name, *args, **kwargs):
        # retrieve check from official repo
        check_repository_uri = check_name if '/' in check_name else 'tmichelet/dd-%s-check' % check_name

        repo_url = '/'.join([GITHUB_SOURCE, check_repository_uri])
        if requests.get(repo_url).status_code == 404:
            raise CheckNotFound()

        # initialize directory
        _agent_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')

        check_directory = os.path.join(_agent_path, CHECKS_PATH, check_repository_uri)
        if not os.path.exists(check_directory):
            os.makedirs(check_directory)

        # download files
        for filename in REQUIRED_FILES:
            file_url = '/'.join([GITHUB_CONTENT, check_repository_uri, DEFAULT_VERSION, filename])
            file_path = os.path.join(check_directory, filename)
            r = requests.get(file_url)
            with open(file_path, 'w') as _file:
                _file.write(r.content)

        return 0
