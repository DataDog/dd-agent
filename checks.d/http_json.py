from checks import AgentCheck
import urllib2
import json

class HTTPJSONCheck(AgentCheck):
    def check(self, instance):
        if 'url' not in instance:
            self.log.info("Skipping instance, no url found.")
            return

        default_timeout = self.init_config.get('default_timeout', 5)
        timeout = float(instance.get('timeout', default_timeout))

        tags = instance.get('tags', None)
        url = instance['url']

        self.log.debug('Fetching JSON metrics at url: %s' % url)

        # Read our URL 
        json_data = urllib2.urlopen(url, timeout=timeout)

        # Load the JSON
        fetched_metrics = json.load(json_data)

        num_metrics_returned = len(fetched_metrics)
        gauge_metrics = 0
        counter_metrics = 0

        for metric in fetched_metrics:
            metric_id = instance['prefix'] + metric
            if instance['metrics'][metric] == 'gauge':
                self.gauge(metric_id, fetched_metrics[metric], tags=tags)
                gauge_metrics += 1
            elif instance['metrics'][metric] == 'counter':
                self.count(metric_id, fetched_metrics[metric], tags=tags)
                counter_metrics += 1
            else:
                self.log.debug('Unconfigured metric present in JSON: %s' % metric )

        self.log.debug('Fetched %d metrics from %s' % (num_metrics_returned, url))
        self.log.debug('- Parsed %d gauge metrics' % (gauge_metrics))
        self.log.debug('- Parsed %d counter metrics' % (counter_metrics))

        return



if __name__ == '__main__':
    check, instances = HTTPJSONCheck.from_yaml('/etc/dd-agent/conf.d/http_json.yaml')
    for instance in instances:
        print "\nRunning the check against url: %s" % (instance['url'])
        check.check(instance)
        if check.has_events():
            print 'Events: %s' % (check.get_events())
        print 'Metrics: %s' % (check.get_metrics())

