# stdlib
import os

# 3p
import requests

# project

GITHUB_CONTENT = 'https://raw.githubusercontent.com'
GITHUB_SOURCE = 'https://github.com/'

OFFICIAL_REPOSITORY = '%s/tmichelet/dd-checks/master/checks.json' % GITHUB_CONTENT

CHECKS_PATH = 'checks.e'

DEFAULT_VERSION = 'master'
REQUIRED_FILES = ['check.py', 'check.yaml.example']


class CheckNotFound(Exception):
    pass


class CheckManager(object):
    """
    TODO
    """

    @classmethod
    def install(cls, check_name, *args, **kwargs):
        # retrieve check from official repo
        checks_list = requests.get(OFFICIAL_REPOSITORY).json()
        if check_name not in checks_list:
            raise CheckNotFound()

        # initialize directory
        check_repository = checks_list[check_name]
        check_repository_uri = check_repository.replace(GITHUB_SOURCE, '')
        check_directory = os.path.join(CHECKS_PATH, check_repository_uri)
        if not os.path.exists(check_directory):
            os.makedirs(check_directory)

        # download files
        for filename in REQUIRED_FILES:
            file_url = '/'.join([GITHUB_CONTENT, check_repository_uri, DEFAULT_VERSION, filename])
            file_path = os.path.join(check_directory, filename)
            r = requests.get(file_url)
            with open(file_path, 'w') as _file:
                _file.write(r.content)

        return 1
