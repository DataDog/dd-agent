# stdlib
import unittest

# 3rd party
import mock

# project
from utils.dockerutil import DockerUtil


class TestDockerUtil(unittest.TestCase):
    def test_parse_subsystem(self):
        lines = [
            # (line, expected_result)
            (
                # Kubernetes < 1.6
                ['10', 'memory', '/2ea504688cad325b9105f183b0d7831266a05f95b513c7327a6e9989ce8a450a'],
                '2ea504688cad325b9105f183b0d7831266a05f95b513c7327a6e9989ce8a450a'
            ), (
                # New CoreOS / most systems
                ['10', 'memory', '/docker/2ea504688cad325b9105f183b0d7831266a05f95b513c7327a6e9989ce8a450a'],
                'docker/2ea504688cad325b9105f183b0d7831266a05f95b513c7327a6e9989ce8a450a'
            ), (
                # Unidentified legacy system?
                ['10', 'memory', '2ea504688cad325b9105f183b0d7831266a05f95b513c7327a6e9989ce8a450a'],
                '2ea504688cad325b9105f183b0d7831266a05f95b513c7327a6e9989ce8a450a'
            ), (
                # Rancher
                ['10', 'memory', '/docker/864daa0a0b19aa4703231b6c76f85c6f369b2452a5a7f777f0c9101c0fd5772a/docker/3bac629503293d1bb61e74f3e25b6c525f0c262f22974634c5d6988bb4b07927'],
                'docker/3bac629503293d1bb61e74f3e25b6c525f0c262f22974634c5d6988bb4b07927'
            ), (
                # Legacy CoreOS 7xx
                ['7', 'memory', '/system.slice/docker-71116698eb215f2a5819f11ece7ea721f0e8d45169c7484d1cd7812596fad454.scope'],
                'system.slice/docker-71116698eb215f2a5819f11ece7ea721f0e8d45169c7484d1cd7812596fad454.scope'
            ), (
                # Kubernetes >= 1.6 QoS cgroups
                ['7', 'memory', '/kubepods/burstable/poda0f63163-3fa8-11e7-a098-42010a840216/7e071d0086ebe623dcbf3a7e0005f23eb08d7ea4df4bb42075df43c9359ce078'],
                'kubepods/burstable/poda0f63163-3fa8-11e7-a098-42010a840216/7e071d0086ebe623dcbf3a7e0005f23eb08d7ea4df4bb42075df43c9359ce078'
            )
        ]

        du = DockerUtil()
        for line, exp_res in lines:
            self.assertEquals(du._parse_subsystem(line), exp_res)

    def test_image_name_from_container(self):
        co = {'Image': 'redis:3.2'}
        self.assertEqual('redis:3.2', DockerUtil().image_name_extractor(co))

    def test_image_name_from_image_repotags(self):
        du = DockerUtil()
        du._client = mock.MagicMock()
        mock_img = mock.MagicMock(name='inspect_image', return_value = {'RepoTags': ["redis:3.2"], 'RepoDigests': []})
        du._client.inspect_image = mock_img
        sha = 'sha256:e48e77eee11b6d9ac9fc35a23992b4158355a8ec3fd3725526eba3f467e4b6c9'
        co = {'Image': sha}
        self.assertEqual('redis:3.2', DockerUtil().image_name_extractor(co))
        mock_img.assert_called_once_with(sha)

        # Make sure cache is used insead of call again inspect_image
        DockerUtil().image_name_extractor(co)
        mock_img.assert_called_once()

    def test_image_name_from_image_repodigests(self):
        du = DockerUtil()
        du._client = mock.MagicMock()
        du._client.inspect_image = mock.MagicMock(name='inspect_image', return_value = {'RepoTags': [],
            'RepoDigests': ['alpine@sha256:4f2d8bbad359e3e6f23c0498e009aaa3e2f31996cbea7269b78f92ee43647811']})

        co = {'Image': 'sha256:e48e77eee11b6d9ac9fc35a23992b4158355a8ec3fd3725526eba3f467e4b6d9'}
        self.assertEqual('alpine', du.image_name_extractor(co))

    def test_extract_container_tags(self):
        #mocks
        du = DockerUtil()
        with mock.patch.dict(du._image_sha_to_name_mapping,
          {'gcr.io/google_containers/hyperkube@sha256:7653dfb091e9524ecb1c2c472ec27e9d2e0ff9addc199d91b5c532a2cdba5b9e': 'gcr.io/google_containers/hyperkube:latest',
          'myregistry.local:5000/testing/test-image@sha256:5bef08742407efd622d243692b79ba0055383bbce12900324f75e56f589aedb0': 'myregistry.local:5000/testing/test-image:version'}):
            no_label_test_data = [
                # Nominal case
                [{'Image': 'redis:3.2'}, ['docker_image:redis:3.2', 'image_name:redis', 'image_tag:3.2']],
                # No tag
                [{'Image': 'redis'}, ['docker_image:redis', 'image_name:redis']],
                # No image
                [{}, []],
                # Image containing 'sha256', swarm fashion
                [{'Image': 'datadog/docker-dd-agent:latest@sha256:769418c18c3e9e0b6ab2c18147c3599d6e27f40fb3dee56418bf897147ff84d0'},
                    ['docker_image:datadog/docker-dd-agent:latest', 'image_name:datadog/docker-dd-agent', 'image_tag:latest']],
                # Image containing 'sha256', kubernetes fashion
                [{'Image': 'gcr.io/google_containers/hyperkube@sha256:7653dfb091e9524ecb1c2c472ec27e9d2e0ff9addc199d91b5c532a2cdba5b9e'},
                    ['docker_image:gcr.io/google_containers/hyperkube:latest', 'image_name:gcr.io/google_containers/hyperkube', 'image_tag:latest']],
                # Images with several ':'
                [{'Image': 'myregistry.local:5000/testing/test-image:version'},
                    ['docker_image:myregistry.local:5000/testing/test-image:version', 'image_name:myregistry.local:5000/testing/test-image', 'image_tag:version']],
                [{'Image': 'myregistry.local:5000/testing/test-image@sha256:5bef08742407efd622d243692b79ba0055383bbce12900324f75e56f589aedb0'},
                    ['docker_image:myregistry.local:5000/testing/test-image:version', 'image_name:myregistry.local:5000/testing/test-image', 'image_tag:version']],
                # Here, since the tag is present, we should not try to resolve it in the sha256, and so returning 'latest'
                [{'Image': 'myregistry.local:5000/testing/test-image:latest@sha256:5bef08742407efd622d243692b79ba0055383bbce12900324f75e56f589aedb0'},
                    ['docker_image:myregistry.local:5000/testing/test-image:latest', 'image_name:myregistry.local:5000/testing/test-image', 'image_tag:latest']]
            ]
            labeled_test_data = [
                # No labels
                (
                    # ctr inspect
                    {
                        'Image': 'redis:3.2',
                        'Config': {
                            'Labels': {}
                        }
                    },
                    # labels as tags
                    [],
                    # expected result
                    ['docker_image:redis:3.2', 'image_name:redis', 'image_tag:3.2']
                ),
                # Un-monitored labels
                (
                    {
                        'Image': 'redis:3.2',
                        'Config': {
                            'Labels': {
                                'foo': 'bar'
                            }
                        }
                    },
                    [],
                    ['docker_image:redis:3.2', 'image_name:redis', 'image_tag:3.2']
                ),
                # no labels, with labels_as_tags list
                (
                    {
                        'Image': 'redis:3.2',
                        'Config': {
                            'Labels': {}
                        }
                    },
                    ['foo'],
                    ['docker_image:redis:3.2', 'image_name:redis', 'image_tag:3.2']
                ),
                # labels and labels_as_tags list
                (
                    {
                        'Image': 'redis:3.2',
                        'Config': {
                            'Labels': {'foo': 'bar', 'f00': 'b4r'}
                        }
                    },
                    ['foo'],
                    ['docker_image:redis:3.2', 'image_name:redis', 'image_tag:3.2', 'foo:bar']
                ),

            ]
            for test in no_label_test_data:
                self.assertEqual(test[1], du.extract_container_tags(test[0], []))

            for test in labeled_test_data:
                self.assertEqual(test[2], du.extract_container_tags(test[0], test[1]))

    def test_docker_host_metadata_ok(self):
        mock_version = mock.MagicMock(name='version', return_value={'Version': '1.13.1'})
        du = DockerUtil()
        du._client = mock.MagicMock()
        du._client.version = mock_version
        du.swarm_node_state = 'inactive'
        self.assertEqual({'docker_version': '1.13.1', 'docker_swarm': 'inactive'}, du.get_host_metadata())
        mock_version.assert_called_once()

    def test_docker_host_metadata_invalid_response(self):
        mock_version = mock.MagicMock(name='version', return_value=None)
        du = DockerUtil()
        du._client = mock.MagicMock()
        du._client.version = mock_version
        du.swarm_node_state = 'inactive'
        self.assertEqual({'docker_swarm': 'inactive'}, DockerUtil().get_host_metadata())
        mock_version.assert_called_once()

    def test_docker_host_metadata_swarm_ok(self):
        du = DockerUtil()
        mock_version = mock.MagicMock(name='version', return_value={'Version': '1.13.1'})
        mock_isswarm = mock.MagicMock(name='is_swarm', return_value=True)
        du._client = mock.MagicMock()
        du._client.version = mock_version
        du.is_swarm = mock_isswarm

        self.assertEqual({'docker_version': '1.13.1', 'docker_swarm': 'active'}, DockerUtil().get_host_metadata())
        mock_version.assert_called_once()

    def test_docker_are_tags_filtered(self):
        with mock.patch.object(DockerUtil, 'is_k8s', side_effect=lambda: True):
            DockerUtil._drop()
            du = DockerUtil()

            self.assertTrue(du.is_k8s())
            pause_containers = [
                "docker_image:gcr.io/google_containers/pause-amd64:0.3.0",
                "docker_image:asia.gcr.io/google_containers/pause-amd64:3.0",
                "docker_image:k8s.gcr.io/pause-amd64:latest",
                "image_name:openshift/origin-pod",
                "image_name:kubernetes/pause",
            ]
            for image in pause_containers:
                self.assertTrue(du.are_tags_filtered([image]))

            self.assertTrue(pause_containers)
            self.assertFalse(du.are_tags_filtered(["docker_image:quay.io/coreos/etcd:latest"]))
            self.assertFalse(du.are_tags_filtered(["image_name:redis"]))
