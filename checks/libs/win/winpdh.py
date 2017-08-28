import time
import win32pdh

DATA_POINT_INTERVAL = 0.10

class WinPDHCounter(object):
    def __init__(self, class_name, instance_name, log):
        self._class_name = class_name
        self._instance_name = instance_name
        self._is_single_instance = False
        self.hq = win32pdh.OpenQuery()
        self.logger = log
        self.counterdict = {}
        counters, instances = win32pdh.EnumObjectItems(None, None, self._class_name, win32pdh.PERF_DETAIL_WIZARD)
        if len(instances) > 0:
            for inst in instances:
                path = win32pdh.MakeCounterPath((None, self._class_name, inst, None, 0, self._instance_name))
                self.counterdict[inst] = win32pdh.AddCounter(self.hq, path)
                self.logger.debug("Path: %s" % str(path))
        else:
            path = win32pdh.MakeCounterPath((None, self._class_name, None, None, 0, self._instance_name))
            self.logger.debug("Path: %s\n" % str(path))
            try:
                self.counterdict["__single_instance"] = win32pdh.AddCounter(self.hq, path)
            except Exception as e:
                self.logger.fatal("Failed to create counter.  No instances of %s\%s" % (
                    self._class_name, self._instance_name))
                raise
            self._is_single_instance = True

    def __del__(self):
        if(self.hq):
            win32pdh.CloseQuery(self.hq)

    def is_single_instance(self):
        return self._is_single_instance

    def get_single_value(self):
        if not self.is_single_instance():
            raise ValueError('counter is not single instance %s %s' % (
                self._class_name, self._instance_name))

        vals = self.get_all_values()
        return vals["__single_instance"]

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
