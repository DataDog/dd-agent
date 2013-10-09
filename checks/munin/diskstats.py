
from checks.munin import MuninPlugin

class DiskstatsMuninPlugin(MuninPlugin):

    @staticmethod
    def get_name():
        return "diskstats"

    @staticmethod
    def parse_metric(check, section, device, mname, mvalue, mgraph = None):
        """ diskstats metrics:
          - mname = [device]_[metric] or just metric 
          - mgraph: None or [type.device] or just [type]
             type is useless for now, but device is not
        """

        #remove postgres_ from begining, remove trailing _ if any
        if '_' in mname:
            device, mname = mname.split('_',1)

        if mgraph is not None and '.' in mgraph:
            _type, device = mgraph.split('.',1)

        mname = "munin.%s.%s" % (section, mname)

        #FIXME: register device when available 
        #print "Saving diskstat:", mname, device, mvalue
        check.register_metric(mname)
        check.save_sample(mname,mvalue,device_name=device) 
