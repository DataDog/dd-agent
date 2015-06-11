import unittest

from mock import patch
from nose.plugins.attrib import attr

from tests.checks.common import get_check_class


def _mocked_find_cgroup(*args, **kwargs):
    return


@attr(requires='docker')
class DockerCheckTest(unittest.TestCase):
    def test_tag_exclude_all(self):
        """exclude all, except ubuntu and debian."""
        instance = {
            'include': [
                'docker_image:ubuntu',
                'docker_image:debian',
            ],
            'exclude': ['.*'],
        }

        klass = get_check_class('docker')
        # NO-OP but loads the check
        with patch.object(klass, '_find_cgroup', _mocked_find_cgroup):
            check = klass('docker', {}, {})

        check._prepare_filters(instance)
        self.assertEquals(len(instance['exclude_patterns']), 1)
        self.assertEquals(len(instance['include_patterns']), 2)

        truth_table_exclusion = {
            'some_tag': True,
            'debian:ubuntu': True,
            'docker_image:centos': True,
            'docker_image:ubuntu': False,
            'docker_image:debian': False,
        }

        for tag, val in truth_table_exclusion.iteritems():
            self.assertEquals(
                check._is_container_excluded(instance, [tag]),
                val,
                "{0} expected {1} but is not".format(tag, val)
            )

    def test_tag_include_all(self):
        """exclude all, except ubuntu and debian."""
        instance = {
            'include': [],
            'exclude': [
                'docker_image:ubuntu',
                'docker_image:debian',
            ],
        }

        klass = get_check_class('docker')
        # NO-OP but loads the check
        with patch.object(klass, '_find_cgroup', _mocked_find_cgroup):
            check = klass('docker', {}, {})

        check._prepare_filters(instance)
        self.assertEquals(len(instance['exclude_patterns']), 2)
        self.assertEquals(len(instance['include_patterns']), 0)

        truth_table_exclusion = {
            'some_tag': False,
            'debian:ubuntu': False,
            'docker_image:centos': False,
            'docker_image:ubuntu': True,
            'docker_image:debian': True,
        }

        for tag, val in truth_table_exclusion.iteritems():
            self.assertEquals(
                check._is_container_excluded(instance, [tag]),
                val,
                "{0} expected {1} but is not".format(tag, val)
            )
