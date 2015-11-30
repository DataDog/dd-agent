# Datadog
from checks import AgentCheck

# Other
import json
import urllib2
from collections import namedtuple

class PdnsChecks(AgentCheck):


    def _get_pdns_stats(self, instance):
        config = self._get_config(instance)
        request = urllib2.Request(config.pdns_url + ':' + str(config.port) + "/servers/localhost/statistics", headers={"X-API-Key" : config.api_key})
        content = urllib2.urlopen(request).read()
        result = json.loads(content)
        return result

    def check(self, instance):
        stats = self._get_pdns_stats(instance)
        for stat in stats:
            self.gauge('pdns.' + stat['name'], stat['value'])

    def _get_config(self, instance):
        required = ['pdns_url', 'port', 'api_key']
        for param in required:
            if not instance.get(param):
                raise Exception("powerdns-recursor instance missing %s. Skipping." % (param))

        pdns_url = instance.get('pdns_url')
        port = instance.get('port')
        api_key = instance.get('api_key')

        Config = namedtuple('Config', [
            'pdns_url',
            'port',
            'api_key']
        )

        return Config(pdns_url, port, api_key)
