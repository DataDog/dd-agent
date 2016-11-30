# stdlib
import logging
import os
import sys
import unittest

# 3p
from nose.plugins.attrib import attr

# project
import modules

log = logging.getLogger('datadog.test')

TARGET_MODULE = 'tests.core.fixtures.target_module'
default_target = 'DEFAULT'
specified_target = 'SPECIFIED'
has_been_mutated = False


class TestModuleLoad(unittest.TestCase):

    def setUp(self):
        sys.modules[__name__].has_been_mutated = True
        if TARGET_MODULE in sys.modules:
            del sys.modules[TARGET_MODULE]

    def tearDown(self):
        sys.modules[__name__].has_been_mutated = False

    def test_cached_module(self):
        """Modules already in the cache should be reused"""
        self.assertTrue(modules.load('%s:has_been_mutated' % __name__))

    def test_cache_population(self):
        """Python module cache should be populated"""
        self.assertTrue(TARGET_MODULE not in sys.modules)
        modules.load(TARGET_MODULE)
        self.assertTrue(TARGET_MODULE in sys.modules)

    def test_modname_load_default(self):
        """When the specifier contains no module name, any provided default
        should be used"""
        self.assertEquals(
            modules.load(
                TARGET_MODULE,
                'default_target'),
            'DEFAULT'
        )

    def test_modname_load_specified(self):
        """When the specifier contains a module name, any provided default
        should be overridden"""
        self.assertEquals(
            modules.load(
                '{0}:specified_target'.format(TARGET_MODULE),
                'default_target'),
            'SPECIFIED'
        )

    # This test fails on Windows, but we don't really care since it's only used
    # for a deprecated check loading scheme
    @attr('unix')
    def test_pathname_load_finds_package(self):
        """"Loading modules by absolute path should correctly set the name of
        the loaded module to include any package containing it."""
        m = modules.load(os.path.join(os.getcwd(),
                                      TARGET_MODULE.replace('.', '/')))
        self.assertEquals(m.__name__, TARGET_MODULE)
