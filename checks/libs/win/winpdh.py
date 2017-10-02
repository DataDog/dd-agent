import time
import win32pdh
import _winreg

DATA_POINT_INTERVAL = 0.01

class WinPDHCounter(object):
    # store the dictionary of pdh counter names
    pdh_counter_dict = {}

    def __init__(self, class_name, instance_name):
        self._get_counter_dictionary()
        self._class_name = win32pdh.LookupPerfNameByIndex(None, int(WinPDHCounter.pdh_counter_dict[class_name]))
        self._instance_name = win32pdh.LookupPerfNameByIndex(None, int(WinPDHCounter.pdh_counter_dict[instance_name]))
        self.hq = win32pdh.OpenQuery()

    def __del__(self):
        if(self.hq):
            win32pdh.CloseQuery(self.hq)

    def _get_counter_dictionary(self):
        if WinPDHCounter.pdh_counter_dict:
            # already populated
            return

        try:
            val, t = _winreg.QueryValueEx(_winreg.HKEY_PERFORMANCE_DATA, "Counter 009")
        except Exception as e:
            print "Exception %s" % str(e)
            raise

        # create a table of the keys to the counter index, because we want to look up
        # by counter index.
        idx = 0
        idx_max = len(val)
        while idx < idx_max:
            WinPDHCounter.pdh_counter_dict[val[idx+1]] = val[idx]
            idx += 2



class WinPDHSingleCounter(WinPDHCounter):
    def __init__(self, class_name, instance_name):
        WinPDHCounter.__init__(self, class_name, instance_name)
        path = win32pdh.MakeCounterPath((None, self._class_name, None, None, 0, self._instance_name))
        self.counter_handle = win32pdh.AddCounter(self.hq, path)

    def get_single_value(self):
        win32pdh.CollectQueryData(self.hq)
        t, val = win32pdh.GetFormattedCounterValue(self.counter_handle, win32pdh.PDH_FMT_LARGE)
        return val

class WinPDHMultiCounter(WinPDHCounter):
    def __init__(self, class_name, instance_name):
        WinPDHCounter.__init__(self, class_name, instance_name)
        self.counterdict = {}
        counters, instances = win32pdh.EnumObjectItems(None, None, self._class_name, win32pdh.PERF_DETAIL_WIZARD)
        for inst in instances:
            path = win32pdh.MakeCounterPath((None, self._class_name, inst, None, 0, self._instance_name))
            self.counterdict[inst] = win32pdh.AddCounter(self.hq, path)

    def get_all_values(self):
        ret = {}

        # self will retrieve the list of all object names in the class (i.e. all the network interface
        # names in the class "network interface"
        counters, instances = win32pdh.EnumObjectItems(None, None, self._class_name, win32pdh.PERF_DETAIL_WIZARD)
        win32pdh.CollectQueryData(self.hq)
        for inst, counter_handle in self.counterdict.iteritems():
            try:
                t, val = win32pdh.GetFormattedCounterValue(counter_handle, win32pdh.PDH_FMT_LONG)
                ret[inst] = val
            except Exception as e:
                # exception usually means self type needs two data points to calculate. Wait
                # a bit and try again
                time.sleep(DATA_POINT_INTERVAL)
                win32pdh.CollectQueryData(self.hq)
                # if we get exception self time, just return it up
                try:
                    t, val = win32pdh.GetFormattedCounterValue(counter_handle, win32pdh.PDH_FMT_LONG)
                    ret[inst] = val
                except Exception as e:
                    raise e
        return ret
