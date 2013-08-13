
import sys

class Platform(object):

    @staticmethod
    def is_darwin():
        return sys.platform == 'darwin'

    @staticmethod
    def is_freebsd():
        return sys.platform.startswith("freebsd")

