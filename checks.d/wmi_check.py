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

    def _get_wmi_conn(self, host, **kwargs):
        """
        Connect to WMI (default to localhost on the root\CIMV2 WMI namespace).
        Turn off introspection by setting `find_classes` to False.
        """
        key = "{0}:".format(host)
        key += ":".join(str(v) for v in kwargs.values())
        if key not in self.wmi_conns:
            self.wmi_conns[key] = wmi.WMI(host, find_classes=False, **kwargs)
        return self.wmi_conns[key]

    def check(self, instance):
        """
        Run WMI check on `instance`.

        Note: by default a WMI query will return all the properties of a class in each instance.
        Specify them to avoid any expensive lookups.
        """
        host = instance.get('host', None)
        namespace = instance.get('namespace', None)
        user = instance.get('username', None)
        password = instance.get('password', None)
        w = self._get_wmi_conn(host, namespace=namespace, user=user, password=password)
        wmi_class = instance.get('class')
        metrics = instance.get('metrics')
        filters = instance.get('filters')
        tag_by = instance.get('tag_by')
        tag_queries = instance.get('tag_queries')
        constant_tags = instance.get('constant_tags')

        # Get properties so it can be specified in the query
        properties = map(lambda x: x[0], metrics)

        if not wmi_class:
            raise Exception('WMI instance is missing a value for `class` in wmi_check.yaml')

        # If there are filters, we need one query per filter.
        if filters:
            for f in filters:
                field = f.keys()[0]
                search = f.values()[0]
                if SEARCH_WILDCARD in search:
                    search = search.replace(SEARCH_WILDCARD, '%')
                    wql = "SELECT {properties} FROM {wclass} WHERE {field} LIKE '{search}'".format(
                        properties=", ".join(properties),
                        wclass=wmi_class,
                        field=field,
                        search=search
                    )
                    results = w.query(wql)
                else:
                    results = getattr(w, wmi_class)(properties, **f)
                self._extract_metrics(results, metrics, tag_by, w, tag_queries, constant_tags)
        else:
            results = getattr(w, wmi_class)(properties)
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
                else:
                    try:
                        val = float(getattr(res, wmi_property))
                    except ValueError:
                        self.log.warning("When extracting metrics with WMI, found a non digit value"
                                         " for property '{0}'.".format(wmi_property))
                        continue
                    except AttributeError:
                        self.log.warning("'{0}' WMI class has no property '{1}'."
                                         .format(res.__class__.__name__, wmi_property))
                        continue

                # Submit the metric to Datadog
                try:
                    func = getattr(self, mtype)
                except AttributeError:
                    raise Exception('Invalid metric type: {0}'.format(mtype))

                func(name, val, tags=tags)
