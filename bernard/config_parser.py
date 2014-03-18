""" Bernard config parsing functions
"""
# stdlib
import glob
import logging
import os.path

# project
from config import get_confd_path, get_config
from util import (
    get_os,
    yaml,
    yLoader,
)

log = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 5
DEFAULT_PERIOD = 15


def get_bernard_config():
    """ Return a dict of configuration from datadog.conf that bernard cares
        about, e.g.: default timeout and period.
    """
    confd_path = get_confd_path(get_os())
    confd_files = glob.glob(os.path.join(confd_path, '*.yaml'))
    return {
        'checks': read_service_checks(confd_files, _get_default_options())
    }


def read_service_checks(confd_files, default_options):
    """ Return a list of configuration for every check that's defined among the
        conf.d file paths in `confd_files`. The `default_options` argument
        includes any global defaults that should apply to any check if not
        defined at a lower level, e.g. timeout.

        The returned structure should match the following:

            [{
                'name': 'check_pg',
                'command': '/usr/local/bin/check_pg -d mydb -p 5432',
                'tags': ['db:mydb', 'port:5432', ...],
                'options': {'timeout': 5, 'period': 15}
            }, ...]
    """
    service_checks = []

    # Build up a list of conf.d configs parsed into python objects.
    # We'll ignore any configs that don't include any service checks.
    for confd_file in confd_files:
        f = open(confd_file)
        try:
            # We're not going to error when the over config format isn't
            # correct (e.g. missing instances). We'll leave that up to
            # the collector. We _will_ warn if the service check config
            # doesn't match what we expect.
            check_config = yaml.load(f.read(), Loader=yLoader)
            service_checks_config = check_config.get('service_checks') or []
            if not service_checks_config:
                log.debug("No service checks defined in %s" % confd_file)
                continue
        finally:
            f.close()

        for name, checks in sorted(service_checks_config.iteritems()):
            # Merge the given options with the defaults.
            for check in checks:
                options = check.get('options') or {}

                # Make sure that every value in `default_options` has a
                # value in the check options. If not, use the default.
                for opt, default in default_options.iteritems():
                    if opt not in options:
                        options[opt] = default

                tags_dict = check.get('tags') or {}
                tags = ['%s:%s' % (k, v) for k, v in tags_dict.iteritems()]

                service_checks.append({
                    'name': name,
                    'command': check['command'],
                    'tags': tags,
                    'options': options
                })

    return service_checks


def _get_default_options():
    """ Returns the global default options for all checks. """
    c = get_config()
    return {
        'period': int(c.get('bernard_default_period', DEFAULT_PERIOD)),
        'timeout': int(c.get('bernard_default_timeout', DEFAULT_TIMEOUT))
    }
