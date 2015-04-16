"""
Generic option parsers that can be used to retrieve
and validate configuration values
"""

# stdlib
import logging
import re


log = logging.getLogger('config')


class Parser(object):
    def __init__(self, name, comment=None, default=None):
        self.name = name
        self.comment = comment
        self.default = default
        self.value = None

    def parse(self, value):
        raise NotImplementedError("A parser should implement parse()")


class BoolOption(Parser):
    TRUTHY_VALS = [
        'y',
        'yes',
        'true',
        'enabled',
        '1',
    ]

    def parse(self, value):
        self.value = value.strip().lower() in self.TRUTHY_VALS


class StringOption(Parser):
    def parse(self, value):
        self.value = value.strip()


class URLOption(Parser):
    def parse(self, value):
        # TODO: urlparse
        self.value = value


class APIKeyOption(Parser):
    VALID_FORMAT = re.compile(r'[a-z0-9]{32}')

    def parse(self, value):
        value = value.strip()
        if not self.VALID_FORMAT.match(value):
            raise ValueError("An API key is a 0-9, a-z 32-long string")

        self.value = value


class HistogramAggrOption(Parser):
    ALL_VALUES = ['min', 'max', 'median', 'avg', 'count']
    DEFAULT_VALUES = ['max', 'median', 'avg', 'count']

    def parse(self, value):
        vals = value.split(',')
        self.values = []

        for val in vals:
            val = val.strip()
            if val not in self.ALL_VALUES:
                log.warning("Ignored histogram aggregate {0}, invalid".format(val))
                continue
            else:
                result.append(val)
    except Exception:
        log.exception("Error when parsing histogram aggregates, skipping")
        return None

    return result

def get_histogram_percentiles(configstr=None):
    if configstr is None:
        return None

    result = []
    try:
        vals = configstr.split(',')
        for val in vals:
            try:
                val = val.strip()
                floatval = float(val)
                if floatval <= 0 or floatval >= 1:
                    raise ValueError
                if len(val) > 4:
                    log.warning("Histogram percentiles are rounded to 2 digits: {0} rounded"\
                        .format(floatval))
                result.append(float(val[0:4]))
            except ValueError:
                log.warning("Bad histogram percentile value {0}, must be float in ]0;1[, skipping"\
                    .format(val))
    except Exception:
        log.exception("Error when parsing histogram percentiles, skipping")
        return None

    return result

