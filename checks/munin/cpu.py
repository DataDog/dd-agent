
from checks.munin import MuninPluginMetricIsDevice

class CpuMuninPlugin(MuninPluginMetricIsDevice):

    @staticmethod
    def get_name():
        return "cpu"

