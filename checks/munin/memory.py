
from checks.munin import MuninPluginMetricIsDevice

class MemoryMuninPlugin(MuninPluginMetricIsDevice):

    @staticmethod
    def get_name():
        return "memory"

