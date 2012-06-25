// TODO: Make allTags and metricId not global.
allTags = [];
metricId = 0;

/* Metric.js
 * Defines Metric data objects, such as Line and Histogram.
 *
 *	updateMostRecent() 		: updates the Metric's mostRecent object
 *	pushRecent()			: pushes the Metric's mostRecent object onto data
 *	shiftOld()				: shifts off the Metric's oldest datapoint
 *	isTimedOut()			: returns whether a metric has timed out
 */

// TODO: Fix inheritance / static / private manipulation here

var Metric = function(options) {
	this.n 			= PupController.n();		// defines number of datapoints in a graph
	this.createdAt 	= new Date();				// creation timestamp. used in sorting by time added
	this.uuid 		= metricId++;				// used in selection. TODO: Might not be needed.
	this.name		= options.metric;			// name of metric. used for sorting by name
	this.type		= options.type;				// type of metric.
	this.tags		= options.tags;				// tags. used for listing tags
	this.max 		= 0.0;						// maximum value. used for determining the y range
	this.data		= [];						// data series for a metric
	this.mostRecent;							// what's updated when new data comes in and 
												// 	what's pushed onto data

	for (var i = 0; i < this.tags.length; i++) {
		var tag = this.tags[i];
		if (-1 === allTags.indexOf(tag)) {
			allTags.push(tag);					// used for tag filtering
		}
	}
};


function Histogram(options) {
	Metric.call(this, options);

	// allow access from a closure	
	var n = this.n;

	this.data = d3.range(options.points.length-1).map(function(d, i) {
		return {
			"name"   : options.points[i].stackName,
			"values" : d3.range(n).map(function() {
				return {"time": +options.now, "value": 0};
			})
		};
	});

	this.mostRecent = options.points.map(function(stk) {
		return {
	   		"name"   : stk.stackName,
			"values" : {time: +options.now, value: 0}
		};
	});	

	var max = this.max;
	this.updateMostRecent = function(incomingMetric, metric) {
		this.mostRecent = incomingMetric.points.map(function(stk) {
			return {
				"name" 	 : stk.stackName,
				"values" : stk.values.map(function(d) {
					if (d[1] > max) { max = d[1]; }
					return {
						"time" 	: d[0] * 1000,
						"value" : d[1]
					};
				})[0] // should make continuous
			};
		});
		this.max = max;
	}

	this.pushRecent = function(timedOut, now) {
		if (timedOut) {
			this.data = this.data.map(function(stk) {
				return stk.values.push({time: +now, value: 0});
			});
		} else {
			for (var i = 0; i < this.data.length; i++) {
				this.mostRecent[i].values.time = +now;
				this.data[i].values.push(this.mostRecent[i].values);
				// TODO: Ensure proper ordering of stacks.
			}
		}
	}

	this.shiftOld = function() {
		for (var i = 0; i < this.data.length; i++) {
			this.data[i].values.shift();
		}
	}	
	
	this.isTimedOut = function(now, timeout) {
		return now - d3.min(this.mostRecent, function(stk) { 
			return stk.time; 
		}) > timeout ? true: false;
	}
}


function Line(options) {
	Metric.call(this, options);

	this.data = d3.range(this.n).map(function() {
		return {"time": +options.now, "value": 0};
	});

	this.mostRecent = {"time": +options.now, "value": 0};

	var max = this.max;
	this.updateMostRecent = function(incomingMetric, metric) {
		this.mostRecent = incomingMetric.points.map(function(d) {
			if (d[1] > max) { max = d[1]; }
			return {
				"time"  : d[0] * 1000,
				"value" : d[1]
			};
		})[0]; // should make continuous
		this.max = max;
	}

	this.pushRecent = function(timedOut, now) {
		if (timedOut) {
			this.data.push({time: +now, value: 0});
		} else {
			this.mostRecent.time = +now;
			this.data.push(this.mostRecent);
		}
	}

	this.shiftOld = function() {
		this.data.shift();
	}

	this.isTimedOut = function(now, timeout) {
		return now - this.mostRecent.time > timeout ? true : false;
	}
}

