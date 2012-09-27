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
                wmi_cls = getattr(w, wmi_name)()
            except AttributeError:
                self.logger.error("Unable to find the '%s' WMI class. Skipping." \
                    % wmi_name)
                continue

            if not len(wmi_cls):
                self.logger.error("No values in the '%s' WMI class" % wmi_name)
                continue

            for device in wmi_cls:
                # There's only one value under this class, just use that one
                try:
                    val = getattr(device, wmi_val)
                except AttributeError:
                    self.logger.error("'%s' WMI class does not have value for %s" \
                        % (wmi_name, wmi_val))
                    break

                # If len > 1, we want to tag by name
                if len(wmi_cls) > 1:
                    tags = ['name:%s' % self.normalize_device_name(device.name)]
                else:
                    tags = None

                try:
                    val = float(val)
                except:
                    self.logger.error('Unable to parse %s/%s as a metric. The value %s can not be parsed as a float' % (wmi_name, wmi_val, val))
                    continue

                self.save_gauge(metric_name, val, tags=tags)

        return self.get_metrics()
