# stdlib
import os
import unittest

# 3p
import mock

# project
import utils.hostname


class FakeUtil(object):
    def __init__(self, value):
        self.value = value

    def get_hostname(self, **kwargs):
        return self.value


FIXTURE_PATH = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    'fixtures',
    'hostname',
    'hostname_results'
)


def read_fixtures():
    return open(FIXTURE_PATH).read().splitlines()


def write_fixtures(results):
    with open(FIXTURE_PATH, 'w') as f:
        for line in results:
            f.write(line + '\n')


def combine_possibilities(possibilities):
    combined = []
    current_choices = possibilities[0]
    if len(possibilities) == 1:
        return map(lambda x: [x], current_choices)
    for poss in combine_possibilities(possibilities[1:]):
        for choice in current_choices:
            combined.append([choice] + poss)
    return combined


class NoLog(object):
    def warning(self, *args, **kwargs):
        pass


def value_of_mock(mocked):
    if type(mocked) == FakeUtil:
        return mocked.get_hostname()
    else:
        return mocked


class TestGetHostname(unittest.TestCase):
    _PLATFORM_FUNCTIONS = [
        'is_linux',
        'is_containerized',
        'is_ecs'
    ]
    _PLATFORM_POSSIBILITIES = [
        # is_linux, is_containerized, is_ecs
        [True, True, True],
        [True, True, False],
        [True, False, True],
        [True, False, False],
        [False, False, False],
    ]

    _HOSTNAME_FUNCTIONS = [
        'utils.hostname.get_config_hostname',
        'utils.hostname.GCE.get_hostname',
        'utils.hostname.DockerUtil',
        'utils.hostname.KubeUtil',
        'utils.hostname._get_hostname_unix',
        'utils.hostname.EC2.get_instance_id',
        'socket.gethostname',
    ]

    _HOSTNAME_POSSIBILITIES = [
        [None, 'localhost', 'config-hostname'],
        [None, 'localhost', 'gce-hostname'],
        [FakeUtil(None), FakeUtil('localhost'), FakeUtil('ip-42-42-42-42'), FakeUtil('docker-hostname')],
        [FakeUtil(None), FakeUtil('localhost'), FakeUtil('ip-42-42-42-42'), FakeUtil('kube-hostname')],
        [None, 'localhost', 'ip-42-42-42-42', 'unix-hostname'],
        [None, 'instance-id-hostname'],
        [None, 'localhost', 'ip-43-43-43-43', 'socket-hostname']
    ]

    _IMBREAKINGCOMPATIBILITYANDIKNOWIT = False

    @mock.patch('utils.hostname.log', return_value=NoLog())
    def test_hostname_resolution(self, log_mock):
        combined_possibilities = combine_possibilities(self._HOSTNAME_POSSIBILITIES)
        result = []
        expected_results = read_fixtures()
        poss_number = -1
        for possibility in self._PLATFORM_POSSIBILITIES:
            patches = []
            for i, plat_func in enumerate(self._PLATFORM_FUNCTIONS):
                patches.append(mock.patch('utils.hostname.Platform.%s' % plat_func, return_value=possibility[i]))
                patches[i].start()

            for host_poss in combined_possibilities:
                host_patches = []
                for i, host_func in enumerate(self._HOSTNAME_FUNCTIONS):
                    host_patches.append(mock.patch(host_func, return_value=host_poss[i]))
                    host_patches[i].start()
                try:
                    poss_number += 1
                    result.append(utils.hostname.get_hostname())
                except Exception:
                    result.append('No hostname found')
                if not self._IMBREAKINGCOMPATIBILITYANDIKNOWIT:
                    if result[-1] != expected_results[poss_number]:
                        raise Exception(
                            """
is_linux: %s, is_containerized: %s, is_ecs: %s

get_config_hostname: %s
GCE.get_hostname: %s
DockerUtil.get_hostname: %s
KubeUtil.get_hostname: %s
_get_hostname_unix: %s
EC2.get_instance_id: %s
socket.gethostname: %s

result: %s, expected: %s
                            """ % tuple(possibility + map(value_of_mock, host_poss) + [result[-1], expected_results[poss_number]])
                        )

                for host_patch in host_patches:
                    host_patch.stop()

            for patch in patches:
                patch.stop()

        if self._IMBREAKINGCOMPATIBILITYANDIKNOWIT:
            write_fixtures(result)
