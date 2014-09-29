import sys
import os
import logging
import unittest

import modules

log = logging.getLogger('datadog.test')

default_target = 'DEFAULT'
specified_target = 'SPECIFIED'
has_been_mutated = False

class TestModuleLoad(unittest.TestCase):

    def setUp(self):
        sys.modules[__name__].has_been_mutated = True
        if 'tests.target_module' in sys.modules:
            del sys.modules['tests.target_module']

    def tearDown(self):
        sys.modules[__name__].has_been_mutated = False

    def test_cached_module(self):
        """Modules already in the cache should be reused"""
        self.assertTrue(modules.load('%s:has_been_mutated' % __name__))

    def test_cache_population(self):
        """Python module cache should be populated"""
        self.assertTrue(not 'tests.target_module' in sys.modules)
        modules.load('tests.target_module')
        self.assertTrue('tests.target_module' in sys.modules)

    def test_modname_load_default(self):
        """When the specifier contains no module name, any provided default
        should be used"""
        self.assertEquals(
            modules.load(
                'tests.target_module',
                'default_target'),
            'DEFAULT'
        )

    def test_modname_load_specified(self):
        """When the specifier contains a module name, any provided default
        should be overridden"""
        self.assertEquals(
            modules.load(
                'tests.target_module:specified_target',
                'default_target'),
            'SPECIFIED'
        )

    def test_pathname_load_finds_package(self):
        """"Loading modules by absolute path should correctly set the name of
        the loaded module to include any package containing it."""
        m = modules.load(os.getcwd() + '/tests/target_module.py')
        self.assertEquals(m.__name__, 'tests.target_module')

if __name__ == '__main__':
    unittest.main()
