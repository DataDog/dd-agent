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

    @mock.patch('docker.Client.inspect_image')
    @mock.patch('docker.Client.__init__')
    def test_image_name_from_image_repotags(self, mock_init, mock_image):
        mock_image.return_value = {'RepoTags': ["redis:3.2"], 'RepoDigests': []}
        mock_init.return_value = None
        sha = 'sha256:e48e77eee11b6d9ac9fc35a23992b4158355a8ec3fd3725526eba3f467e4b6c9'
        co = {'Image': sha}
        self.assertEqual('redis:3.2', DockerUtil().image_name_extractor(co))
        mock_image.assert_called_once_with(sha)

        # Make sure cache is used insead of call again inspect_image
        DockerUtil().image_name_extractor(co)
        mock_image.assert_called_once()

    @mock.patch('docker.Client.inspect_image')
    @mock.patch('docker.Client.__init__')
    def test_image_name_from_image_repodigests(self, mock_init, mock_image):
        mock_image.return_value = {'RepoTags': [],
            'RepoDigests': ['alpine@sha256:4f2d8bbad359e3e6f23c0498e009aaa3e2f31996cbea7269b78f92ee43647811']}
        mock_init.return_value = None
        co = {'Image': 'sha256:e48e77eee11b6d9ac9fc35a23992b4158355a8ec3fd3725526eba3f467e4b6d9'}
        self.assertEqual('alpine', DockerUtil().image_name_extractor(co))

    def test_extract_container_tags(self):
        test_data = [
            # Nominal case
            [{'Image': 'redis:3.2'}, ['docker_image:redis:3.2', 'image_name:redis', 'image_tag:3.2']],
            # No tag
            [{'Image': 'redis'}, ['docker_image:redis', 'image_name:redis']],
            # No image
            [{}, []],
        ]
        for test in test_data:
            self.assertEqual(test[1], DockerUtil().extract_container_tags(test[0]))

    @mock.patch('docker.Client.version')
    @mock.patch('docker.Client.__init__')
    def test_docker_host_tags_ok(self, mock_init, mock_version):
        mock_version.return_value = {'Version': '1.13.1'}
        mock_init.return_value = None
        self.assertEqual(['docker_version:1.13.1'], DockerUtil().get_host_tags())
        mock_version.assert_called_once()

    @mock.patch('docker.Client.version')
    @mock.patch('docker.Client.__init__')
    def test_docker_host_tags_invalid_response(self, mock_init, mock_version):
        mock_version.return_value = None
        mock_init.return_value = None
        self.assertEqual([], DockerUtil().get_host_tags())
        mock_version.assert_called_once()

    @mock.patch('utils.dockerutil.DockerUtil.is_swarm')
    @mock.patch('docker.Client.version')
    @mock.patch('docker.Client.__init__')
    def test_docker_host_tags_swarm_ok(self, mock_init, mock_version, mock_isswarm):
        mock_isswarm.return_value = True
        mock_version.return_value = {'Version': '1.13.1'}
        mock_init.return_value = None
        self.assertEqual(['docker_version:1.13.1', 'docker_swarm:active'], DockerUtil().get_host_tags())
        mock_version.assert_called_once()
