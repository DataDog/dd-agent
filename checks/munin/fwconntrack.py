
from checks.munin import MuninPluginMetricIsDevice

class FwconntrackMuninPlugin(MuninPluginMetricIsDevice):

    @staticmethod
    def get_name():
        return "fw_conntrack"

