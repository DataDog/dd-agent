
class MuninPlugin(object):

    def get_name(self):
        """ Name of the plugin this parser is associated to. The match is made
            on the begining of the plugin name, which means 'postgres' will match
            'postgres*' """
        raise "To be implemented"

    def parse_metrics(self, metrics):
        """Given a dict of metrics, return a tuple:
        (metric namespace, metrics)"""
        raise "To be implemented"
