# stdlib
import errno
import os

# 3p
try:
    import psutil
except ImportError:
    psutil = None

# project
from util import Platform


def pid_exists(pid):
    """
    Check if a pid exists.
    Lighter than psutil.pid_exists
    """
    if psutil:
        return psutil.pid_exists(pid)

    if Platform.is_windows():
        import ctypes  # Available from python2.5
        kernel32 = ctypes.windll.kernel32
        synchronize = 0x100000

        process = kernel32.OpenProcess(synchronize, 0, pid)
        if process != 0:
            kernel32.CloseHandle(process)
            return True
        else:
            return False

    # Code from psutil._psposix.pid_exists
    # See https://github.com/giampaolo/psutil/blob/master/psutil/_psposix.py
    if pid == 0:
        # According to "man 2 kill" PID 0 has a special meaning:
        # it refers to <<every process in the process group of the
        # calling process>> so we don't want to go any further.
        # If we get here it means this UNIX platform *does* have
        # a process with id 0.
        return True
    try:
        os.kill(pid, 0)
    except OSError as err:
        if err.errno == errno.ESRCH:
            # ESRCH == No such process
            return False
        elif err.errno == errno.EPERM:
            # EPERM clearly means there's a process to deny access to
            return True
        else:
            # According to "man 2 kill" possible error values are
            # (EINVAL, EPERM, ESRCH) therefore we should never get
            # here. If we do let's be explicit in considering this
            # an error.
            raise err
    else:
        return True
