# stdlib
from collections import namedtuple

# 3rd
import pywintypes
from win32com.client import Dispatch

# project
from checks import AgentCheck


WMIMetric = namedtuple('WMIMetric', ['name', 'value', 'tags'])


class InvalidWMIQuery(Exception):
    """
    Invalid WMI Query.
    """
    pass


class MissingTagBy(Exception):
    """
    WMI query returned multiple rows but no `tag_by` value was given.
    """
    pass


class WMIAlternativeCheck(AgentCheck):
    """
    An alternative to Datadog agent WMI check.

    Windows only.
    """
    def __init__(self, name, init_config, agentConfig, instances):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances)
        self.wmi_conns = {}
        self.wmi_props = {}

    def check(self, instance):
        """
        Fetch WMI metrics.
        """
        # Connection information
        host = instance.get('host', "localhost")
        namespace = instance.get('namespace', "root\\cimv2")
        username = instance.get('username', "")
        password = instance.get('password', "")

        # WMI instance
        wmi_class = instance.get('class')
        metrics = instance.get('metrics')
        filters = instance.get('filters')
        tag_by = instance.get('tag_by')

        # Get connection, (metric name, metric type) by WMI property map and the property list
        w = self._get_wmi_conn(host, namespace, username, password)
        metric_name_and_type_by_property, properties = self._get_wmi_properties(host, namespace,
                                                                                wmi_class, metrics)

        results = self._query_wmi(w, wmi_class, properties, filters, tag_by)
        metrics = self._extract_metrics(results, tag_by)
        self._submit_metrics(metrics, metric_name_and_type_by_property)

    def _get_wmi_conn(self, host, namespace, username, password):
        """
        Create and cache WMI connections.
        """
        key = "{host}:{namespace}:{username}:{password}".format(
            host=host, namespace=namespace,
            username=username, password=password
        )
        if key not in self.wmi_conns:
            server = Dispatch("WbemScripting.SWbemLocator")
            self.log.debug(u"Connection to {host} with namespace {namespace}".format(
                host=host,
                namespace=namespace
            )
            )
            self.wmi_conns[key] = server.ConnectServer(host, namespace, username, password)
        return self.wmi_conns[key]

    def _get_wmi_properties(self, host, namespace, wmi_class, metrics):
        """
        Create and cache a (metric name, metric type) by WMI property map and a property list.
        """
        key = "{host}:{namespace}:{wmi_class}".format(
            host=host,
            namespace=namespace,
            wmi_class=wmi_class
        )

        if key not in self.wmi_props:
            metric_name_by_property = {
                wmi_property.lower(): (metric_name, metric_type)
                for wmi_property, metric_name, metric_type in metrics
            }
            properties = map(lambda x: x[0], metrics)
            self.wmi_props[key] = (metric_name_by_property, properties)

        return self.wmi_props[key]

    @staticmethod
    def _format_filter(filters):
        """
        Transform filters to a comprehensive WQL `WHERE` clause.
        """
        def build_where_clause(fltr):
            """
            Recursively build `WHERE` clause.
            """
            f = fltr.pop()
            prop, value = f.popitem()

            if len(fltr) == 0:
                return "{property} = '{constant}'".format(
                    property=prop,
                    constant=value
                )
            return "{property} = '{constant}' AND {more}".format(
                property=prop,
                constant=value,
                more=build_where_clause(fltr)
            )

        if not filters:
            return ""

        return " WHERE {clause}".format(clause=build_where_clause(filters))

    def _query_wmi(self, w, wmi_class, wmi_properties, filters, tag_by):
        """
        Query WMI using WMI Query Language (WQL).

        Returns: List of unknown COMObject.
        """
        formated_wmi_properties = ",".join(wmi_properties)
        wql = "Select {properties} from {wmi_class}{filters}".format(
            properties=formated_wmi_properties,
            wmi_class=wmi_class,
            filters=self._format_filter(filters)
        )
        self.log.debug(u"Querying WMI: {0}".format(wql))

        results = w.ExecQuery(wql)

        try:
            self._raise_for_invalid(results, tag_by)
        except InvalidWMIQuery:
            self.log.warning(u"Invalid WMI query: {0}".format(wql))
            results = []
        except MissingTagBy:
            raise Exception(u"WMI query returned multiple rows but no `tag_by` value was given. "
                            "class={wmi_class} - properties={wmi_properties}".format(
                                wmi_class=wmi_class,
                                wmi_properties=wmi_properties
                            )
                            )

        return results

    def _extract_metrics(self, results, tag_by):
        """
        Extract, parse and tag metrics from WMI query results.

        Returns: List of WMIMetric
        ```
        [
            WMIMetric("FreeMegabytes", 19742, ["name:_total"]),
            WMIMetric("AvgDiskBytesPerWrite", 1536, ["name:c:"]),
        ]
        ```
        """
        metrics = []
        for res in results:
            tags = []
            for wmi_property in res.Properties_:
                if wmi_property.Name == tag_by:
                    tags.append(
                        "{name}:{value}".format(
                            name=tag_by.lower(),
                            value=str(wmi_property.Value).lower()
                        )
                    )
                    continue
                try:
                    metrics.append(WMIMetric(wmi_property.Name, float(wmi_property.Value), tags))
                except ValueError:
                    self.log.warning(u"When extracting metrics with WMI, found a non digit value"
                                     " for property '{0}'.".format(wmi_property.Name))
                    continue
        return metrics

    def _submit_metrics(self, metrics, metric_name_and_type_by_property):
        """
        Submit metrics to Datadog with the right name and type.
        """
        for metric in metrics:

            metric_key = (metric.name).lower()
            metric_name, metric_type = metric_name_and_type_by_property[metric_key]

            try:
                func = getattr(self, metric_type)
            except AttributeError:
                raise Exception(u"Invalid metric type: {0}".format(metric_type))

            func(metric_name, metric.value, metric.tags)

    @staticmethod
    def _raise_for_invalid(result, tag_by):
        """
        Raise:
        * `InvalidWMIQuery`: when the result returned by the WMI query is invalid
        * `MissingTagBy`: when the result returned by tge WMI query contains multiple rows
            but no `tag_by` value was given
        """
        try:
            if len(result) > 1 and not tag_by:
                raise MissingTagBy
        except (pywintypes.com_error):
            raise InvalidWMIQuery
