
from checks.munin import MuninPluginMetricIsDevice

class PostfixmailqueueMuninPlugin(MuninPluginMetricIsDevice):

    @staticmethod
    def get_name():
        return "postfix_mailqueue"

