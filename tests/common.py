from config import get_checksd_path
import sys

def get_checksd_module(name):
    checksd_path = get_checksd_path()
    if checksd_path not in sys.path:
        sys.path.append(checksd_path)

    return __import__(name)