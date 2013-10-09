
from checks.munin import MuninPluginMetricIsDevice

class ProcessesMuninPlugin(MuninPluginMetricIsDevice):

    @staticmethod
    def get_name():
        return "processes"

