'''
Windows Only.

Generic WMI check. This check allows you to specify particular metrics that you
want from WMI in your configuration. Check wmi.yaml.example in your conf.d
directory for more details on configuration.
'''
from checks import AgentCheck

class WMICheck(AgentCheck):
    def check(self, instance):
        wmi_class = instance.get('class')
        metrics = instance.get('metrics')
        filters = instance.get('filters')
        tag_by = instance.get('tag_by')

        if not wmi_class:
            raise Exception('WMI instance is missing a value for `class` in wmi.yaml')

        import wmi
        w = wmi.WMI()

        # If there are filters, we need one query per filter.
        if filters:
            for f in filters:
                results = getattr(w, wmi_class)(**f)
                self._extract_metrics(results, metrics, tag_by)
        else:
            results = getattr(w, wmi_class)()
            self._extract_metrics(results, metrics, tag_by)

    def _extract_metrics(self, results, metrics, tag_by):
        if len(results) > 1 and tag_by is None:
            raise Exception('WMI query returned multiple rows but no `tag_by` value was given. metrics=%s' % metrics)

        for wmi_property, name, mtype in metrics:
            for res in results:
                val = float(getattr(res, wmi_property))

                # Grab the tag from the result if there's a `tag_by` value (e.g.: "name:jenkins")
                if tag_by:
                    tags = ['%s:%s' % (tag_by.lower(), getattr(res, tag_by))]
                else:
                    tags = None

                try:
                    func = getattr(self, mtype)
                except AttributeError:
                    raise Exception('Invalid metric type: {0}'.format(mtype))

                # submit the metric to datadog
                func(name, val, tags=tags)

    @staticmethod
    def parse_agent_config(agentConfig):
        if not agentConfig.get('WMI'):
            return False

        config = []
        metrics = agentConfig['WMI']
        for metric_name, wmi_conf in metrics.items():
            try:
                wmi_class, wmi_prop = wmi_conf.split(':')
            except ValueError:
                self.logger.error('Invalid WMI line format: %s' % wmi_conf)

            config.append({
                'class': wmi_class,
                'metrics': [[wmi_prop, metric_name, 'gauge']]
            })

        return config
