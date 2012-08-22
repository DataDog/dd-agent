from munin import Munin

class MuninPlugin(object):

    @staticmethod
    def get_name():
        """ Name of the plugin this parser is associated to. The match is made
            on the begining of the plugin name, which means 'postgres' will match
            'postgres*' """
        raise "To be implemented"

    @staticmethod
    def parse_metric(check, section, device, mname, mvalue, mgraph = None):
        """Given a section (name of munin script), a metric name and a value, register
        it as a metric and save the value if needed:
            - check: a Munin object, which inherits from checks, allowing to call
          counter/gauge and save_sample
            - section: name of the munin script which generated the metric
            - device: a preparsed device for the metric (may be None)
            - mname: metric name
            - mvalue: metric value (as a string)
            - mgraph: the multigraph identifier, if any
        """
        raise "To be implemented"


class MuninPluginMetricIsDevice(MuninPlugin):
    """Use the metric name as a device"""

    @staticmethod
    def parse_metric(check, section, device, mname, mvalue, mgraph = None):

        device = mname
        mname = "munin." + section
        if mgraph is not None:
            mname = mname + "." + mgraph
        check.register_metric(mname)
        #print "Saving with device:", mname, device, mvalue
        check.save_sample(mname, mvalue)
