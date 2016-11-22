import time
import sys
import win32pdh
import psutil

class WinPDHCounter(object):
    
    def __init__(self, class_name, instance_name):
        self._class_name = class_name
        self._instance_name = instance_name

    def get_single_value(self):
        hq = win32pdh.OpenQuery()
        path = win32pdh.MakeCounterPath((None, self._class_name, None, None, 0, self._instance_name))
        counter_handle = win32pdh.AddCounter(hq, path)
        win32pdh.CollectQueryData(hq)
        t, val = win32pdh.GetFormattedCounterValue(counter_handle, win32pdh.PDH_FMT_LARGE)
        win32pdh.CloseQuery(hq)
        return val

    def get_all_values(self):
        ret = {}

        # self will retrieve the list of all object names in the class (i.e. all the network interface
        # names in the class "network interface"
        counters, instances = win32pdh.EnumObjectItems(None, None, self._class_name, win32pdh.PERF_DETAIL_WIZARD)
        for inst in instances:
            hq = win32pdh.OpenQuery()
            path = win32pdh.MakeCounterPath((None, self._class_name, inst, None, 0, self._instance_name))
            counter_handle = win32pdh.AddCounter(hq, path)
    
            win32pdh.CollectQueryData(hq)
            try:
                t, val = win32pdh.GetFormattedCounterValue(counter_handle, win32pdh.PDH_FMT_LONG)
                ret[inst] = val
            except Exception as e:
                # exception usually means self type needs two data points to calculate. Wait
                # a bit and try again
                time.sleep(0.01)
                win32pdh.CollectQueryData(hq)
                # if we get exception self time, just return it up
                try:
                    t, val = win32pdh.GetFormattedCounterValue(counter_handle, win32pdh.PDH_FMT_LONG)
                    ret[inst] = val
                except Exception as e:
                    win32pdh.CloseQuery(hq)
                    raise e
            win32pdh.CloseQuery(hq)
        return ret
