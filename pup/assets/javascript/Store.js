/* Store.js
 * A datastore which stores all the metric objects for MetricGraph to later graph.
 *
 * Public interface:
 *  save()              : iterates through incoming metric data, creates new metrics,
 *                          and updates data. Returns success and error codes.
 *                              0 - normal
 *                              1 - malformed incoming data
 *                              2 - hit graph limit
 *  getMetrics()        : returns all metrics in datastore as an array
 *  getMetricByName()   : returns a metric by name. Returns undefined if the metric
 *                          doesn't exist. 
 */

var Store = function() {
    var metricsByName = {},
        limit = 20,
        limitErrorShown = false;

    // private helpers ---------------------------------------------------------
    
    // creates and return a certain type of Metric based on incoming metric type
    var createMetric = function(incoming, metric) {
        var MetricClass;
        if (incoming[metric].type === "histogram") {
            MetricClass = Histogram;
        } else if (incoming[metric].type !== "histogram") {
            MetricClass = Line;
        } // may be more types

        return new MetricClass({
            now: new Date(),
            metric: metric,
            type: incoming[metric].type,
            tags: incoming[metric].tags || [],
            freq: incoming[metric].freq,
            points: incoming[metric].points
        });
    };

    // runs checks on incoming data to verify its format and source
    var isReady = function(incoming) {
        if ("Waiting" in incoming) { return false; }
        return true;
    };

    // verifies data
    var verify = function(incomingMetric) {
        if (incomingMetric.type
                && incomingMetric.freq
                && incomingMetric.points) { return true; }
        return false;
    };

    // public interface ---------------------------------------------------------
    var pub = {};

    // iterates through incoming metric data, creates new metrics, and updates data
    pub.save = function(incoming) {
        if (isReady(incoming)) {
            for (var metric in incoming) {
                if (incoming.hasOwnProperty(metric) && verify(incoming[metric])) {  
                    if ( !(metric in metricsByName) ) {
                        if ( Object.keys(metricsByName).length < limit) {
                            metricsByName[metric] = createMetric(incoming, metric); 
                        } else if (!limitErrorShown) {
                            limitErrorShown = true;
                            return 2;
                        }
                    }
                    if (metric in metricsByName) {
                        metricsByName[metric].updateMostRecent(incoming[metric], metric);
                    }
                } else {
                    return 1;
                }
            }
            return 0;
        }
    };

    // accessor for all the metrics. Returns an array of all metrics in plotsByName
    pub.getMetrics = function() {
        var metrics = [];
        for (var metric in metricsByName) {
            if (metricsByName.hasOwnProperty(metric)) {
                metrics.push(metricsByName[metric]);
            }
        }
        return metrics;
    };

    // accessor for a particular metric by name
    pub.getMetricByName = function(name) {
        return metricsByName[name];
    };

    return pub;
}();
