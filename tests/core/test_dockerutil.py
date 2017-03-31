# stdlib
import unittest

# project
from utils.dockerutil import DockerUtil


class TestDockerUtil(unittest.TestCase):

    def test_parse_subsystem(self):
        lines = [
            # (line, expected_result)
            (
                ['10', 'memory', '/2ea504688cad325b9105f183b0d7831266a05f95b513c7327a6e9989ce8a450a'],
                '2ea504688cad325b9105f183b0d7831266a05f95b513c7327a6e9989ce8a450a'
            ), (
                ['10', 'memory', '/docker/2ea504688cad325b9105f183b0d7831266a05f95b513c7327a6e9989ce8a450a'],
                'docker/2ea504688cad325b9105f183b0d7831266a05f95b513c7327a6e9989ce8a450a'
            ), (
                ['10', 'memory', '2ea504688cad325b9105f183b0d7831266a05f95b513c7327a6e9989ce8a450a'],
                '2ea504688cad325b9105f183b0d7831266a05f95b513c7327a6e9989ce8a450a'
            ), (
                ['10', 'memory', '/docker/864daa0a0b19aa4703231b6c76f85c6f369b2452a5a7f777f0c9101c0fd5772a/docker/3bac629503293d1bb61e74f3e25b6c525f0c262f22974634c5d6988bb4b07927'],
                'docker/3bac629503293d1bb61e74f3e25b6c525f0c262f22974634c5d6988bb4b07927'
            )
        ]

        du = DockerUtil()
        for line, exp_res in lines:
            self.assertEquals(du._parse_subsystem(line), exp_res)
