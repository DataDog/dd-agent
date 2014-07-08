import urllib2
import simplejson as json
from checks import AgentCheck

class GoExpvar(AgentCheck):

    def __init__(self, name, init_config, agentConfig, instances=None):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances)
        self.func= {
                "gauge" : self.gauge,
                "rate"  : self.rate
                }


    def check(self, instance):
        if 'expvar_url' not in instance:
            raise Exception('GoExpvar instance missing "expvar_url" value.')
        tags = instance.get('tags', [])
        content = self._get_data(instance)
        data = json.loads(content)
        self.parse_expvar_data(instance, data)

    def _get_data(self, instance):
        '''
        Query the expvar http server for the json
        document containing all metrics
        '''
        url = instance.get('expvar_url')
        req = urllib2.Request(url)
        response = urllib2.urlopen(req)
        body = response.read()
        return body

    def parse_expvar_data(self, instance, content):
        '''
        Report all the metrics based on the configuration in instance
        If a metric is not well configured or is not present in the payload,
        continue processing metrics but log the information to the info page
        '''
        tags = instance.get("tags", [])
        for metric in instance.get("metrics", []):
            if "path" not in metric:
                self.warning("Metric %s has no path" % metric)
                continue
            metric_type = metric.get("type", "gauge")
            if metric_type not in self.func:
                self.warning("Metric type %s not supported for this check" % metric_type)
                continue

            path = metric.get("path")
            keys = path.split("/")
            try:
                value = self.deep_get(content, keys)
            except (KeyError, IndexError, TypeError):
                self.log.warning("Could not get value for path %s,"
                                 " check the schema of your json" % path)
                continue

            metric_name = metric.get("name", keys[-1])
            metric_name = self.normalize(metric_name, "go_expvar", fix_case=True)

            self.func[metric_type](metric_name, value, tags)

    def deep_get(self, content, keys):
        '''
        Allow to retrieve content nested inside a several layers deep dict/list

        Example: -content: {
                            "key1": {
                                "key2" : [
                                            {
                                                "name"  : "object1",
                                                "value" : 42
                                            },
                                            {
                                                "name"  : "object2",
                                                "value" : 72
                                            }
                                          ]
                            }
                        }
                  -keys: ["key1", "key2", "1", "value"]

                  would return 72
        '''
        key = int(keys[0]) if isinstance(content, list) else keys[0]
        if len(keys) == 1:
            return content[key]
        else:
            # Sadly no TRO in python but this recursion isn't deep
            return self.deep_get(content[key],keys[1:])


