/* Store.js
 * A datastore which stores all the metric objects for MetricGraph to later graph.
 *
 * Public interface:
 * 	save() 				: iterates through incoming metric data, creates new metrics,
 * 							and updates data. Returns success and error codes.
 * 								0 - normal
 * 								1 - malformed incoming data
 * 								2 - hit graph limit
 * 	getMetrics() 		: returns all metrics in datastore as an array
 * 	getMetricByName() 	: returns a metric by name. Returns undefined if the metric
 * 							doesn't exist. 
 */

var Store = function() {
	var metricsByName = {},
		limit = 20,
		limitErrorShown = false;

	// private helpers ---------------------------------------------------------
	
	// creates and return a certain type of Metric based on incoming metric type
	var createMetric = function(incoming, metric) {
		if (incoming[metric].type === "histogram") {
			metricClass = Histogram;
		} else if (incoming[metric].type !== "histogram") {
			metricClass = Line;
		} // may be more types

		return new metricClass({
			now: new Date(),
			metric: metric,
			type: incoming[metric].type,
			tags: incoming[metric].tags || [],
			points: incoming[metric].points
		});
	}

	// runs checks on incoming data to verify its format and source
	var verify = function(incoming) {
		if ("Waiting" in incoming) {
			return false;
		}

		// TODO: Implement more checks
		return true;
	}

	// public interface ---------------------------------------------------------
	pub = {};

	// iterates through incoming metric data, creates new metrics, and updates data
	// TODO: Break up save. It might be doing too much.
	pub.save = function(incoming) {
		if (verify(incoming)) {
			for (var metric in incoming) {
				if (incoming.hasOwnProperty(metric)) {	
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
				}
			}
			return 0;
		}
	}

	// accessor for all the metrics. Returns an array of all metrics in plotsByName
	pub.getMetrics = function() {
		var metrics = [];
		for (var metric in metricsByName) metrics.push(metricsByName[metric]);
		return metrics;
	}

	// accessor for a particular metric by name
	pub.getMetricByName = function(name) {
		return metricsByName[name];
	}

	return pub;
}();
