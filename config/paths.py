from utils.platform import Platform

def windows_common_path(suffix=None)
    """Return the common appdata path, using ctypes
    From http://stackoverflow.com/questions/626796/how-do-i-find-the-windows-common-application-data-folder-using-python
    """
    import ctypes
    from ctypes import wintypes, windll

    CSIDL_COMMON_APPDATA = 35

    _SHGetFolderPath = windll.shell32.SHGetFolderPathW
    _SHGetFolderPath.argtypes = [wintypes.HWND,
                                ctypes.c_int,
                                wintypes.HANDLE,
                                wintypes.DWORD, wintypes.LPCWSTR]

    path_buf = wintypes.create_unicode_buffer(wintypes.MAX_PATH)
    result = _SHGetFolderPath(0, CSIDL_COMMON_APPDATA, 0, 0, path_buf)
    return path_buf.value


def get_default_checksd_path():
    if Platform.is_win32():
        return windows_common_path(os.path.join('Datadog', 'checks.d'))
    else:
        return '/etc/dd-agent/checks.d'

def get_local_forwarder_url():
    return 'http://localhost:17123'
