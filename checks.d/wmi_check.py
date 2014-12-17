'''
Windows Only.

Generic WMI check. This check allows you to specify particular metrics that you
want from WMI in your configuration. Check wmi.yaml.example in your conf.d
directory for more details on configuration.
'''
# project
from checks import AgentCheck

# 3rd party
import wmi

UP_METRIC = 'Up'
SEARCH_WILDCARD = '*'

class WMICheck(AgentCheck):
    def __init__(self, name, init_config, agentConfig):
        AgentCheck.__init__(self, name, init_config, agentConfig)
        self.wmi_conns = {}

    def _get_wmi_conn(self, host, user, password):
        key = "%s:%s:%s" % (host, user, password)
        if key not in self.wmi_conns:
            self.wmi_conns[key] = wmi.WMI(host, user=user, password=password)
        return self.wmi_conns[key]

    def check(self, instance):
        host = instance.get('host', None)
        user = instance.get('username', None)
        password = instance.get('password', None)
        w = self._get_wmi_conn(host, user, password)

        wmi_class = instance.get('class')
        metrics = instance.get('metrics')
        filters = instance.get('filters')
        tag_by = instance.get('tag_by')
        link = instance.get('link_tag')
        constant_tag = instance.get('constant_tags')

        if not wmi_class:
            raise Exception('WMI instance is missing a value for `class` in wmi_check.yaml')

        # If there are filters, we need one query per filter.
        if filters:
            for f in filters:
                prop = f.keys()[0]
                search = f.values()[0]
                if SEARCH_WILDCARD in search:
                    search = search.replace(SEARCH_WILDCARD, '%')
                    wql = "SELECT * FROM %s WHERE %s LIKE '%s'" \
                                                % (wmi_class, prop, search)
                    results = w.query(wql)
                else:
                    results = getattr(w, wmi_class)(**f)
                self._extract_metrics(results, metrics, tag_by, w, link, constant_tag)
        else:
            results = getattr(w, wmi_class)()
            self._extract_metrics(results, metrics, tag_by, w, link, constant_tag)

    def _extract_metrics(self, results, metrics, tag_by, wmi, link, constant_tag):
        if len(results) > 1 and tag_by is None:
            raise Exception('WMI query returned multiple rows but no `tag_by` value was given. metrics=%s' % metrics)

        for res in results:
            tags = []
            
            # include any constant tags...
            if constant_tag:
                for c in constant_tag:
                    tags.append(c)
                    
            # if link is specified then get attribute from another class and use it as a tag
            link_prop = ""
            link_value = ""
            if link:
                source_val = float(getattr(res, link[0]))
                link_prop = link[3]
                link_results = wmi.query("SELECT {0} FROM {1} WHERE {2} = {3}".format(link_prop, link[1], link[2], source_val))
                if len(link_results) == 1:
                    link_value = getattr(link_results[0], link_prop).lower()
                    p = 0
                    for part in link_value.split():
                        tags.append("{0}{1}:{2}".format(link_prop.lower(), p, part.strip()))
                        p += 1
                else:
                    self.log.warning("Failed to find {0} for {1} {2}. No metrics gathered".format(link[1], link[2], source_val))
                    continue

            # Grab the tag from the result if there's a `tag_by` value (e.g.: "name:jenkins")
            # strip any #instance off the value. WMI does this to give unique names
            # the link_tag enhancement gives us unique tags
            if tag_by:
                tag_value = getattr(res, tag_by).lower()
                if link and tag_value.find("#") > 0:
                    tag_value = tag_value[:tag_value.find("#")]
                tags.append('%s:%s' % (tag_by.lower(), tag_value))

            if len(tags) == 0:
                tags = None
                
            for wmi_property, name, mtype in metrics:
                if wmi_property == UP_METRIC:
                    # Special-case metric will just submit 1 for every value
                    # returned in the result.
                    val = 1
                else:
                    val = float(getattr(res, wmi_property))

                try:
                    func = getattr(self, mtype)
                except AttributeError:
                    raise Exception('Invalid metric type: {0}'.format(mtype))

                # submit the metric to datadog
                func(name, val, tags=tags)
