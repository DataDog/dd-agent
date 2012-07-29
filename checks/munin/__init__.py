from munin import Munin

class MuninPlugin(object):

    @staticmethod
    def get_name():
        """ Name of the plugin this parser is associated to. The match is made
            on the begining of the plugin name, which means 'postgres' will match
            'postgres*' """
        raise "To be implemented"

    @staticmethod
    def parse_metric(check, section, mname, mvalue):
        """Given a section (name of munin script), a metric name and a value, register
        it as a metric and save the value if needed:
            - check: a Munin object, which inherits from checks, allowing to call
          counter/gauge and save_sample
            - seciton: name of the munin script which generated the metric
            - mname: metric name
            - mvalue: metric value (as a string)"""
        raise "To be implemented"
