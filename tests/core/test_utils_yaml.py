# stdlib
import os
import unittest
import tempfile

# project
import yaml

from utils.ddyaml import (
    monkey_patch_pyyaml,
    monkey_patch_pyyaml_reverse,
    safe_yaml_dump_all,
    safe_yaml_load_all,
    safe_yaml_load,
    yDumper,
)

FIXTURE_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'fixtures', 'checks')

class Dummy(object):
    def __init__(self):
        self.foo = 1
        self.bar = 'a'
        self.qux = {self.foo: self.bar}

    def get_foo(self):
        return self.foo

    def get_bar(self):
        return self.bar

    def get_qux(self):
        return self.qux


class UtilsYAMLTest(unittest.TestCase):

    def setUp(self):
        monkey_patch_pyyaml()

    def tearDown(self):
        monkey_patch_pyyaml_reverse()

    def test_monkey_patch(self):
        self.assertTrue(yaml.dump_all == safe_yaml_dump_all)
        self.assertTrue(yaml.load_all == safe_yaml_load_all)
        self.assertTrue(yaml.load == safe_yaml_load)

    def test_load(self):
        conf = os.path.join(FIXTURE_PATH, "valid_conf.yaml")
        with open(conf) as f:
            stream = f.read()

            yaml_config_safe = safe_yaml_load(stream)
            yaml_config_native = yaml.load(stream)
            self.assertTrue(yaml_config_safe is not None)
            self.assertTrue(yaml_config_native is not None)
            self.assertTrue(yaml_config_native == yaml_config_safe)

            yaml_config_safe = [entry for entry in safe_yaml_load_all(stream)]
            yaml_config_native = [entry for entry in yaml.load_all(stream)]
            self.assertTrue(yaml_config_safe is not [])
            self.assertTrue(yaml_config_native is not [])
            self.assertTrue(len(yaml_config_safe) == len(yaml_config_native))
            for safe, native in zip(yaml_config_safe, yaml_config_native):
                self.assertTrue(safe == native)

    def test_unsafe(self):
        dummy = Dummy()

        with self.assertRaises(yaml.representer.RepresenterError):
            yaml.dump_all([dummy])

        with self.assertRaises(yaml.representer.RepresenterError):
            yaml.dump(dummy, Dumper=yDumper)

        # reverse monkey patch and try again
        monkey_patch_pyyaml_reverse()

        with tempfile.TemporaryFile(suffix='.yaml') as f:
            yaml.dump_all([dummy], stream=f)
            f.seek(0)  # rewind

            doc_unsafe = yaml.load(f)
            self.assertTrue(type(doc_unsafe) is Dummy)

            monkey_patch_pyyaml()
            with self.assertRaises(yaml.constructor.ConstructorError):
                f.seek(0)  # rewind
                safe_yaml_load(f)

            with self.assertRaises(yaml.constructor.ConstructorError):
                f.seek(0)  # rewind
                yaml.load(f)
