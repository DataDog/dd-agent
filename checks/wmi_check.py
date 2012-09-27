'''
Windows Only.

Generic WMI check. This check allows you to specify particular metrics that you
want from WMI in your configuration. Check the WMI section in datadog.conf for
more details.
'''
from checks import Check

class WMICheck(Check):
    def check(self, agentConfig):
        if 'WMI' not in agentConfig:
            self.logger.debug("Skipping WMI check. No [WMI] section in config")
            return False

        try:
            import wmi
        except ImportError:
            self.logger.debug("Skipping WMI check. WMI module not available.")
            return False

        metrics = agentConfig['WMI']
        w = wmi.WMI()

        for metric_name, wmi_conf in metrics.items():
            try:
                wmi_name, wmi_val = wmi_conf.split(':')
            except ValueError:
                self.logger.error('Invalid WMI line format: %s' % wmi_conf)
            
            # Get the metric from WMI
            self.gauge(metric_name)
            try:
                res = getattr(w, wmi_name)()[0]
                val = getattr(res, wmi_val)
                try:
                    val = float(val)
                except:
                    self.logger.error('Unable to parse %s/%s as a metric. The value %s can not be parsed as a float' % (wmi_name, wmi_val, val))
                    continue
                self.save_gauge(metric_name, val)
            except:
                self.logger.exception('Unable to get metric %s/%s' % (wmi_name, wmi_val))

        return self.get_metrics()
