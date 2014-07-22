# stdlib
import urllib2

# project
from checks import AgentCheck

# 3rd party
import simplejson as json

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
            values = self.deep_get(content, keys, [])

            if len(values)==1:
                # Defining an alias doesn't make sense if there is several metrics
                metric_name = metric.get("alias")
            for traversed_path, value in values:
                metric_name = metric_name or self.normalize(".".join(traversed_path), "go_expvar", fix_case=True)
                try:
                    float(value)
                except ValueError:
                    self.log.warning("Unreportable value for path %s: %s" % (path,value))
                self.func[metric_type](metric_name, value, tags)

    def deep_get(self, content, keys, traversed_path):
        '''
        Allow to retrieve content nested inside a several layers deep dict/list

        Examples: -content: {
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
                  -keys: ["key1", "key2", "1", "value"] would return [(["key1", "key2", "1", "value"], 72)]
                  -keys: ["key1", "key2", "1", "*"] would return [(["key1", "key2", "1", "value"], 72), (["key1", "key2", "1", "name"], "object2")]
                  -keys: ["key1", "key2", "*", "value"] would return [(["key1", "key2", "1", "value"], 72), (["key1", "key2", "0", "value"], 42)]
        '''
        if keys == []:
            return [(traversed_path, content)]

        key = keys[0]
        if key == '*':
            results = []
            if isinstance(content, list):
                for new_key, new_content in enumerate(content):
                    results.extend(self.deep_get(new_content, keys[1:], traversed_path + [str(new_key)]))
            elif isinstance(content, dict):
                for new_key, new_content in content.items():
                    results.extend(self.deep_get(new_content, keys[1:], traversed_path + [str(new_key)]))
            else:
                # not a traversable structure, it's a value
                results = [(traversed_path, content)]

            return results
        else:
            key = int(key) if isinstance(content, list) else key
            path = traversed_path + [str(key)]
            try:
                if len(keys) == 1:
                    return [(path, content[key])]
                else:
                    return self.deep_get(content[key],keys[1:], path)
            except (KeyError, IndexError, TypeError):
                self.log.warning("Could not get value for path %s,"
                                 " check the schema of your json" % str(path+keys))
                return []

