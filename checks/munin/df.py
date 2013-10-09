
from checks.munin import MuninPluginMetricIsDevice

class DfMuninPlugin(MuninPluginMetricIsDevice):

    @staticmethod
    def get_name():
        return "df"

