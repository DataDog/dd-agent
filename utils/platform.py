import sys


class Platform(object):
    """
    Return information about the given platform.
    """
    @staticmethod
    def is_darwin(name=None):
        name = name or sys.platform
        return 'darwin' in name

    @staticmethod
    def is_mac(name=None):
        return Platform.is_darwin(name)

    @staticmethod
    def is_freebsd(name=None):
        name = name or sys.platform
        return name.startswith("freebsd")

    @staticmethod
    def is_linux(name=None):
        name = name or sys.platform
        return 'linux' in name

    @staticmethod
    def is_bsd(name=None):
        """ Return true if this is a BSD like operating system. """
        name = name or sys.platform
        return Platform.is_darwin(name) or Platform.is_freebsd(name)

    @staticmethod
    def is_solaris(name=None):
        name = name or sys.platform
        return name == "sunos5"

    @staticmethod
    def is_unix(name=None):
        """ Return true if the platform is a unix, False otherwise. """
        name = name or sys.platform
        return (
            Platform.is_darwin()
            or Platform.is_linux()
            or Platform.is_freebsd()
        )

    @staticmethod
    def is_win32(name=None):
        name = name or sys.platform
        return name == "win32"

    @staticmethod
    def is_windows(name=None):
        return Platform.is_win32(name)
