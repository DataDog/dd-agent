import subprocess

from checks import Check

class Varnish(Check):
    def __init__(self, logger):
        Check.__init__(self, logger)

    def check(self, config):
        """Extract stats from varnishstat -1
        When using the -1 option, the columns in the output are, from left to right:
        1. Symbolic entry name
        2. Value
        3. Per-second average over process lifetime, or a period if the value can not be averaged
        4. Descriptive text

        ...
        fetch_204                    0         0.00 Fetch no body (204)
        fetch_304                    0         0.00 Fetch no body (304)
        n_sess_mem                   2          .   N struct 
        sess_memn_sess               0          .   N struct sess
        ...

        How to type metrics? If column 3 is "." it means the metric value in col 2 is a gauge.
        Else the meaningful metric value is column 3 (and it's a gauge too).
        """
        try:
            # Location of varnishstat
            output, error = subprocess.Popen([config.get("varnishstat"), "-1"], stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
            assert error is None
            self.logger.debug("Varnishstats:\n%s" % output)

            for line in output.split("\n"):
                name, gauge_val, rate_val, desc = line.split()
                metric_name = self.normalize(name, prefix="varnish")

                # First time we see the metric?
                if not self.is_metric(metric_name):
                    self.gauge(metric_name)
                    
                # Now figure out which value to pick
                try:
                    if rate_val.lower() in ("nan", "."):
                        # col 2 matters
                        self.save_sample(metric_name, int(gauge_val))
                    else:
                        self.save_sample(metric_name, float(rate_val))
                except TypeError:
                    self.logger.exception("Cannot convert varnish value")
                    
            return self.get_samples_with_timestamps()
                
        except:
            self.logger.exception("Cannot get varnish stats")
            return False

        
