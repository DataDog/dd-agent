'''
Windows Only.

Generic WMI check. This check allows you to specify particular metrics that you
want from WMI in your configuration. Check wmi_check.yaml.example in your conf.d
directory for more details on configuration.
'''
# 3rd party
import wmi

# project
from checks import AgentCheck

UP_METRIC = 'Up'
SEARCH_WILDCARD = '*'


class WMICheck(AgentCheck):
    def __init__(self, name, init_config, agentConfig, instances):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances)
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
        tag_queries = instance.get('tag_queries')
        constant_tags = instance.get('constant_tags')

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
                self._extract_metrics(results, metrics, tag_by, w, tag_queries, constant_tags)
        else:
            results = getattr(w, wmi_class)()
            self._extract_metrics(results, metrics, tag_by, w, tag_queries, constant_tags)

    def _extract_metrics(self, results, metrics, tag_by, wmi, tag_queries, constant_tags):
        if len(results) > 1 and tag_by is None:
            raise Exception('WMI query returned multiple rows but no `tag_by` value was given. '
                            'metrics=%s' % metrics)

        for res in results:
            tags = []

            # include any constant tags...
            if constant_tags:
                tags.extend(constant_tags)

            # if tag_queries is specified then get attributes from other classes and use as a tags
            if tag_queries:
                for query in tag_queries:
                    link_source_property = int(getattr(res, query[0]))
                    target_class = query[1]
                    link_target_class_property = query[2]
                    target_property = query[3]

                    link_results = \
                        wmi.query("SELECT {0} FROM {1} WHERE {2} = {3}"
                                  .format(target_property, target_class,
                                          link_target_class_property, link_source_property))

                    if len(link_results) != 1:
                        self.log.warning("Failed to find {0} for {1} {2}. No metrics gathered"
                                         .format(target_class, link_target_class_property,
                                                 link_source_property))
                        continue

                    link_value = str(getattr(link_results[0], target_property)).lower()
                    tags.append("{0}:{1}".format(target_property.lower(),
                                "_".join(link_value.split())))

            # Grab the tag from the result if there's a `tag_by` value (e.g.: "name:jenkins")
            # Strip any #instance off the value when `tag_queries` is set (gives us unique tags)
            if tag_by:
                tag_value = str(getattr(res, tag_by)).lower()
                if tag_queries and tag_value.find("#") > 0:
                    tag_value = tag_value[:tag_value.find("#")]
                tags.append('%s:%s' % (tag_by.lower(), tag_value))

            if len(tags) == 0:
                tags = None

            for wmi_property, name, mtype in metrics:
                if wmi_property == UP_METRIC:
                    # Special-case metric will just submit 1 for every value
                    # returned in the result.
                    val = 1
                elif getattr(res, wmi_property):
                    val = float(getattr(res, wmi_property))
                else:
                    self.log.warning("When extracting metrics with wmi, found a null value for property '{0}'. "
                                     "Metric type of property is {1}."
                                     .format(wmi_property, mtype))

                try:
                    func = getattr(self, mtype)
                except AttributeError:
                    raise Exception('Invalid metric type: {0}'.format(mtype))

                # submit the metric to datadog
                func(name, val, tags=tags)
