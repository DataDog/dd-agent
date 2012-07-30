""" Tools for loading Python modules from arbitrary locations.
"""

import os
import imp
import sys

def imp_type_for_filename(filename):
    """Given the name of a Python module, return a type description suitable to
    be passed to imp.load_module()"""
    for type_data in imp.get_suffixes():
        extension = type_data[0]
        if filename.endswith(extension):
            return type_data
    return None

def load_qualified_module(full_module_name, path=None):
    """Load a module which may be within a package"""
    remaining_pieces = full_module_name.split('.')
    done_pieces = []
    file_obj = None
    while remaining_pieces:
        try:
            done_pieces.append(remaining_pieces.pop(0))
            curr_module_name = '.'.join(done_pieces)
            (file_obj, filename, description) = imp.find_module(
                    done_pieces[-1], path)
            package_module = imp.load_module(
                    curr_module_name, file_obj, filename, description)
            path = getattr(package_module, '__path__', None) or [filename]
        finally:
            if file_obj:
                file_obj.close()
    return package_module

def module_name_for_filename(filename):
    """Given the name of a Python file, find an appropropriate module name.
    
    This involves determining whether the file is within a package, and
    determining the name of same."""
    all_segments = filename.split(os.sep)
    path_elements = all_segments[:-1]
    module_elements = [all_segments[-1].rsplit('.', 1)[0]]
    while os.path.exists('/'.join(path_elements + ['__init__.py'])):
        module_elements.insert(0, path_elements.pop())
    modulename = '.'.join(module_elements)
    basename = '/'.join(path_elements)
    return (basename, modulename)

def get_module(name):
    """Given either an absolute path to a Python file or a module name, load
    and return a Python module.
    
    If the module is already loaded, takes no action."""
    if name.startswith('/'):
        basename, modulename = module_name_for_filename(name)
        path = [basename]
    else:
        modulename = name
        path = None
    if modulename in sys.modules:
        return sys.modules[modulename]
    return load_qualified_module(modulename, path)

def load(config_string, default_name=None):
    """Given a module name and an object expected to be contained within,
    return said object"""
    (module_name, object_name) = \
            (config_string.rsplit(':', 1) + [default_name])[:2]
    module = get_module(module_name)
    if object_name:
        return getattr(module, object_name)
    else:
        return module
