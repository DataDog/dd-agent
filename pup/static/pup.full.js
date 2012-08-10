/*
 * Constants.js
 * This avoids the hassle of constantly creating new strings.
 * These are common strings.
 */

var C = (function() {
	return {
		WIDTH     : "width",
		HEIGHT    : "height",
		G         : "g",
		TRANSFORM : "transform",
		CLASS     : "class",
		ID        : "id",
		RECT      : "rect",
		TEXT      : "text",
		X         : "x",
		Y         : "y",
		D         : "d",
		PATH      : "path",
		LINE      : "line",
		AREA      : "area",
		PERIOD    : ".",
		HASH      : "#",
		TRANSLATE : "translate",
		OPENPAREN : "(",
		CLOSEPAREN: ")",
		DASH      : "-",
		COMMA     : ",",
		CLIP      : "clip",
		URL       : "url",
		ZERO      : "0",
		HIDDEN    : "hidden",
		TIME      : "time",
		VALUE     : "value",
		NAME      : "name",
		TIME      : "time"
	};
}());
/* Metric.js
 * Defines Metric data objects, such as Line and Histogram.
 *
 *	updateMostRecent()		: updates the Metric's mostRecent object
 *	pushRecent()			: pushes the Metric's mostRecent object onto data
 *	shiftOld()				: shifts off the Metric's oldest datapoint
 *	isTimedOut()			: returns whether a metric has timed out
 */

var allTags = [],
	metricId = 0;

var PupController;
var Metric = function(options) {
	this.n			= PupController.n();		// defines number of datapoints in a graph
	this.createdAt	= new Date();				// creation timestamp. used in sorting by time added
	this.uuid		= metricId++;				// used in selection.
	this.name		= options.metric;			// name of metric. used for sorting by name
	this.type		= options.type;				// type of metric
	this.freq       = options.freq * 1000;      // estimated frequency of sending in milliseconds
	this.tags		= options.tags;				// tags. used for listing tags
	this.max		= 0.0;						// maximum value. used for determining the y range
	this.data		= [];						// data series for a metric
	this.timedOut   = {at: +options.now, is: false};                    // if timedOut

	for (var i = 0; i < this.tags.length; i++) {
		var tag = this.tags[i];
		if (-1 === allTags.indexOf(tag)) {
			allTags[allTags.length] = (tag);					// used for tag filtering
		}
	}
};

function Histogram(options) {
	Metric.call(this, options);

	var n = this.n;

	this.data = d3.range(options.points.length).map(function(d, i) {
		return {
			"name"		: options.points[i].stackName,
			"values"	: [{"time": +options.now, "value": null}]
		};
	});

	this.mostRecent = options.points.map(function(stk) {
		return {
			"name"		: stk.stackName,
			"values"	: {time: +options.now, value: null}
		};
	});
}

Histogram.prototype.updateMostRecent = function(incomingMetric, metric) {
	var max = this.max;
	var average = this.average;
	this.mostRecent = incomingMetric.points.map(function(stk) {
		return {
			"name"		: stk.stackName,
			"values"	: stk.values.map(function(d) {
				if (d[1] > max) { max = d[1]; }
				if (stk.stackName === "avg") { average = d[1]; }
				return {
					"time"	: d[0] * 1000,
					"value"	: d[1]
				};
			})[0]
		};
	});
	this.max = max;
	this.average = average;
};

Histogram.prototype.pushRecent = function() {
	for (var i = 0; i < this.data.length; i++) {
		var mostRecent = {time: this.mostRecent[i].values.time, value: this.mostRecent[i].values.value};
		this.data[i].values[this.data[i].values.length] = mostRecent;
	}
};

Histogram.prototype.pushNull = function(now) {
	this.data = this.data.map(function(stk) {
		stk.values[stk.values.length] = {time: +now, value: null};
		return stk;
	});
};

Histogram.prototype.shiftOld = function(timeWindow) {
	for (var i = 0; i < this.data.length; i++) {
		while (this.data[i].values[0].time < timeWindow) {
			if (this.max === this.data[i].values[0].value) {
				this.resetMax();
			}
			this.data[i].values.shift();
		}
	}
};

Histogram.prototype.setIfTimedOut = function(now) {
	this.timedOut.is = +now - d3.min(this.mostRecent, function(stk) {
		return stk.values.time;
	}) > this.freq * 2 ? true : false;
	if (this.timedOut.is) { this.timedOut.at = +now; }
};

Histogram.prototype.hasNewData = function() {
	return d3.min(this.mostRecent, function(stk) {
		return stk.values.time;
	}) > d3.min(this.data, function(stk) {
		return stk.values[stk.values.length-1].time;
	});
};

Histogram.prototype.resetMax = function() {
	var max = this.max;
	this.data.map(function(stk) {
		stk.values.map(function(d) {
			if (d.value > max) { max = d.value; }
		});
	});
	this.max = max;
};

Histogram.prototype.toCSV = function() {
	var csv = 'time,';
	var sampleStack = this.data[0];
	a = sampleStack;
	for (var i = -1, dataCount = sampleStack.values.length; i < dataCount; i++) {
		var line = '';
		if (i === -1) {
			for (var stkI = 0, stackCount = this.data.length; stkI < stackCount; stkI++) {
				if (line !== '') { line += ","; }
				line += this.data[stkI].name;
			}
		} else {
			if (sampleStack.values[i]
					&& sampleStack.values[i].value == null) { continue; }
			line += sampleStack.values[i].time;
			for (var stkI = 0, stackCount = this.data.length; stkI < stackCount; stkI++) {
				if (line !== '') { line += ","; }
				line += this.data[stkI].values[i].value;
			}
		}
		csv += line + '</br>';
	}
	return csv;
};

function Line(options) {
	Metric.call(this, options);
	this.data = [{"time": +options.now, "value": null}];
	this.mostRecent = [{"time": +options.now, "value": null}];
}

Line.prototype.updateMostRecent = function(incomingMetric, metric) {
	var max = this.max;
	this.mostRecent[0] = incomingMetric.points.map(function(d) {
		if (d[1] > max) { max = d[1]; }
		return {
			"time"  : d[0] * 1000,
			"value" : d[1]
		};
	})[0]; // should make continuous
	this.max = max;
};

Line.prototype.pushNull = function(now) {
	this.data[this.data.length] = {time: +now, value: null};
};

Line.prototype.pushRecent = function() {
	var mostRecent = {time: this.mostRecent[0].time, value: this.mostRecent[0].value};
	this.data[this.data.length] = mostRecent;
};

Line.prototype.shiftOld = function(timeWindow) {
	while (this.data[0].time < timeWindow) {
		if (this.max === this.data[0].value) { this.resetMax(); }
		this.data.shift();
	}
};

Line.prototype.setIfTimedOut = function(now) {
	this.timedOut.is = +now - this.mostRecent[0].time > this.freq * 2 ? true : false;
	if (this.timedOut.is) { this.timedOut.at = +now; }
};

Line.prototype.hasNewData = function() {
	return this.mostRecent[0].time > this.data[this.data.length-1].time;
};

Line.prototype.resetMax = function() {
	var max = this.max;
	this.data.map(function(d, i) {
		if (d.value > max && i > 0) {
			max = d.value;
		}
	});
	this.max = max;
};

Line.prototype.toCSV = function() {
	var csv = '';
	var data = this.data;
	for (var i = -1, len = data.length; i < len; i++) {
		var line = '';
		if (i === -1) {
			for (var index in data[0]) {
				if (line !== '') { line += ","; }
				line += index;
			}
		} else {
			if (data[i].value == null) { continue; }
			for (var index in data[i]) {
				if (data[i].hasOwnProperty(index)) {
					if (line !== '') { line += ","; }
					line += data[i][index];
				}
			}
		}
		csv += line += '</br>';
	}
	return csv;
};
/* Store.js
 * A datastore which stores all the metric objects for MetricGraph to later graph.
 *
 * Public interface:
 *	save()				: iterates through incoming metric data, creates new metrics,
 *							and updates data. Returns success and error codes.
 *								0 - normal
 *								1 - malformed incoming data
 *								2 - hit graph limit
 *	getMetrics()		: returns all metrics in datastore as an array
 *	getMetricByName()	: returns a metric by name. Returns undefined if the metric
 *							doesn't exist.
 */

var Store = function() {
	var metricsByName = {},
		limit = 20,
		limitErrorShown = false;


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

	var isReady = function(incoming) {
		if ("Waiting" in incoming) { return false; }
		return true;
	};

	var verify = function(incomingMetric) {
		if (incomingMetric.type
				&& incomingMetric.freq
				&& incomingMetric.points) { return true; }
		return false;
	};

	var pub = {};

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

	pub.getMetrics = function() {
		var metrics = [];
		for (var metric in metricsByName) {
			if (metricsByName.hasOwnProperty(metric)) {
				metrics.push(metricsByName[metric]);
			}
		}
		return metrics;
	};

	pub.getMetricByName = function(name) {
		return metricsByName[name];
	};

	return pub;
}();
/* PupSocket.js
 * Abstraction for WebSocket.
 * Creates WebSocket connection and redirects incoming data to storage.
 *
 * Public interface:
 *	tryStart()		: creates WebSocket connection if unestablished.
 *	isEstablished()	: returns a boolean value representing whether a WebSocket
 *					  connection was tried and established.
 *	isClosed()		: returns a boolean value representing whether the WebSocket
 *					  connection was closed.
 */

var PupSocket = function(port, save) {
	var connEstablished = false,
		hitLimitOnce = false;

	var setEstablished = function(bool) {
		connEstablished = bool;
	};

	var pub = {};

	pub.isEstablished = function() {
		return connEstablished;
	};

	pub.tryStart = function(port) {
		if (this.isEstablished()) { return; }
		var ws = new WebSocket("ws://" + window.location.hostname +":" + port + "/pupsocket");

		setEstablished(true);

		ws.onmessage = function(evt) {
			var incoming;
			try { incoming = JSON.parse(evt.data); }
			catch (err) {
				setEstablished(false);
				throw "There was an error parsing the incoming data: " + err;
			}

			var attempt = save(incoming);
			switch(attempt) {
				case 0:
					break;
				case 1:
					setEstablished(false);
					throw "Malformed data sent to client";
				case 2:
					if (!hitLimitOnce) {
						var hitLimit = document.getElementById("limit-error");
						hitLimit.innerHTML = "You have reached the graph count limit. This limit is enforced for reasons of performance.";
						setTimeout(function() {
							hitLimit.innerHTML = "";
						}, 5000);
						hitLimitOnce = true;
					}
					break;
			}
		};

		ws.onclose = function() {
			setEstablished(false);
		};

		ws.onerror = function() {
			setEstablished(false);
		};

		return pub;
	};

	pub.isClosed = function() { return false === connEstablished; };

	return pub;
}(port, Store.save);
/* MetricGraph.js
 * Defines how a metric visual is plotted and represented in the side bar. The graphic counterpart
 * to Metric, which solely represents a metric data structure.
 *
 * See Constants.js for "C" properties. They are strings meant to avoid static string creation
 * on every iteration.
 */

var MetricGraph = function(options) {

/*
 *	now - n * duration			now - duration			now
	|---------------------------------|--------------------|
				VISIBLE					INVISIBLE

	Having new points append in the invisible section allows
	the transitions to appear smoothly and not jerky.
*/


	var margin		= {top: 10, right: 24, bottom: 18, left: 45},
		latestBuff  = 10,
		width		= 470 - margin.right,
		height		= 140 - margin.top - margin.bottom,
		yBuffer		= 1.3;

	this.n			= options.n;
	this.duration	= options.duration;
	this.metric		= options.metric;
	this.element	= options.element;
	this.height		= height;
	this.width		= width;
	this.finishedProgress = false;

	var then		= options.now - (this.n - 2) * this.duration,
		now			= options.now - this.duration,
		interpolation = "basis",
		metric      = this.metric;

	this.x = d3.time.scale()
			.domain([then, now])
			.range([0, width]);

	this.y = d3.scale.linear()
			.range([height, 0]);

	var x = this.x,
		y = this.y;

	this.format = d3.format(".3s");

	this.svg = this.element.select(".plot")
		.append("svg")
			.attr(C.WIDTH, width + margin.left + margin.right + latestBuff)
			.attr(C.HEIGHT, height + margin.top + margin.bottom)
		.append(C.G)
			.attr(C.WIDTH, width + margin.left - margin.right)
 			.attr(C.TRANSFORM, C.TRANSLATE + C.OPENPAREN + margin.left + C.COMMA + margin.top + C.CLOSEPAREN);

	this.xAxis = this.svg.append(C.G)
			.attr(C.CLASS, "x axis")
			.attr(C.TRANSFORM, "translate(0," + height + C.CLOSEPAREN)
			.call(this.x.axis = d3.svg.axis().scale(this.x)
										.orient("bottom")
										.ticks(5)
										.tickSize(-this.height)
										.tickPadding(4)
										.tickSubdivide(true));

	this.yAxis = this.svg.append(C.G)
			.attr(C.CLASS, "y axis")
			.call(this.y.axis = d3.svg.axis().scale(this.y)
										.orient("left")
										.ticks(5)
										.tickFormat(this.format));

	var ANTIALIAS = 0.5;

	this.line = d3.svg.line()
		.interpolate(interpolation)
		.defined(function(d) { return d.value != null; })
		.x(function(d) { return x(d.time) + ANTIALIAS; })
		.y(function(d) { return y(d.value) + ANTIALIAS; });

	this.area = d3.svg.area()
		.interpolate(interpolation)
		.defined(this.line.defined())
		.x(this.line.x())
		.y0(function(d) { return height; })
		.y1(this.line.y());

	this.clippedWidth = x(now - metric.freq);

	this.svg.append("defs").append("clipPath")
			.attr(C.ID, function(d,i) {
			   return "clip" + metric.uuid + C.DASH + i;
			})
		.append("rect")
			.attr(C.WIDTH, this.clippedWidth)
			.attr(C.HEIGHT, height);

	this.latest = this.svg.selectAll("text.label")
			.data(metric.mostRecent)
		.enter().append("text")
			.attr(C.CLASS, "latest-val")
			.attr(C.ID, function(d, i) {
				return C.TEXT + metric.uuid + C.DASH + i;
			})
			.attr(C.TRANSFORM, C.TRANSLATE + C.OPENPAREN + this.clippedWidth + C.COMMA + height + C.CLOSEPAREN);

	var progressBarWidth = 40,
		progressBarHeight = 10;

	this.progressBar = this.svg.append(C.G)
		.attr(C.ID, "progress-wrapper" + metric.uuid);

	this.progressBar.append("rect")
		.attr(C.CLASS, "progress-container")
		.attr(C.X, width * 0.5 - progressBarWidth * 0.5)
		.attr(C.Y, height * 0.5 - progressBarHeight * 0.5)
		.attr(C.WIDTH, progressBarWidth)
		.attr(C.HEIGHT, progressBarHeight);

	this.progressBar.append("rect")
		.attr(C.CLASS, "progress")
		.attr(C.ID, "progress" + metric.uuid)
		.attr(C.X, width * 0.5 - progressBarWidth * 0.5)
		.attr(C.Y, height * 0.5 - progressBarHeight * 0.5)
		.attr(C.WIDTH, 0)
		.attr(C.HEIGHT, progressBarHeight);

	this.element.append("ul")
			.attr(C.CLASS, "graph-tags")
			.text("tags: ")
		.selectAll("li")
			.data(metric.tags)
		.enter().append("li")
			.attr(C.CLASS, "graph-tag")
			.attr("tag", function(d) { return d; })
			.text(function(d) { return d; });

	d3.select("#tag-list").selectAll("li")
			.data(allTags)
		.enter().append("li")
			.attr("tag", function(d) { return d; })
			.attr(C.CLASS, "tag")
			.text(function(d) { return d; });

	this.updateScales = function(now) {
		this.x.domain([now - (this.n - 2) * this.duration, now - this.duration]);
		this.y.domain([0, yBuffer * metric.max]);
		if (metric.max === 0) {
			this.y.domain([0, 1]);
		}
	};

	this.tryDrawProgress = function(now) {
		if (!this.finishedProgress) {
			var timePassed = +now - metric.createdAt;
			if (timePassed > metric.freq * 2) {
				d3.select("#progress-wrapper" + metric.uuid)
					.classed("hidden", true);
				this.finishedProgress = true;
			} else {
				d3.select("#progress" + metric.uuid).transition()
					.duration(100)
					.ease("linear")
					.attr(C.WIDTH, timePassed * 20 / metric.freq);
			}
		}
	};
};



var LineGraph = function(options) {
	MetricGraph.call(this, options);

	var graph = this,
		metric = this.metric;

	graph.element.select(".type-symbol")
		.append("img")
			.attr("src", "/pup-line.png");;

	graph.path = graph.svg.append(C.G)
			.attr("clip-path", function(d, i) {
				return "url(#clip" + metric.uuid + C.DASH + i + C.CLOSEPAREN;
			})
		.append(C.PATH)
			.data([metric.data])
			.attr(C.CLASS, C.AREA)
			.attr(C.ID, C.AREA + metric.uuid)
			.attr(C.D, graph.area);

	graph.stroke = graph.svg.append(C.G)
		.attr("clip-path", function(d, i) {
		   return "url(#clip" + metric.uuid + C.DASH + i + C.CLOSEPAREN;
		})
	.append(C.PATH)
		.data([metric.data])
		.attr(C.CLASS, C.LINE)
		.attr(C.ID, C.LINE + metric.uuid)
		.attr(C.D, graph.line);

	graph.updateLatestVal = function(now) {
		if (metric.timedOut.is || +now - metric.timedOut.at < metric.freq * 2) {
			graph.latest.classed("hidden", true);
		} else {
			graph.latest.text(graph.format(metric.mostRecent[0].value))
				.classed("hidden", false);
		}
	};

	graph.redraw = function(now) {
		var g_element = graph.element;

		g_element.select(C.HASH + C.AREA + metric.uuid)
				.attr(C.D, graph.area)
				.attr(C.TRANSFORM, null);

		g_element.select(C.HASH + C.LINE + metric.uuid)
				.attr(C.D, graph.line)
				.attr(C.TRANSFORM, null);

		g_element.select(C.HASH + C.TEXT + metric.uuid + C.DASH + C.ZERO).transition()
			.attr(C.TRANSFORM, C.TRANSLATE + C.OPENPAREN + (graph.clippedWidth + 4)
					+ C.COMMA + (graph.y(metric.mostRecent[0].value) + 3) + C.CLOSEPAREN);

		graph.xAxis.call(graph.x.axis);

		graph.yAxis.call(graph.y.axis);

		var xTransition = graph.x(now - (graph.n - 1) * graph.duration);
		graph.path.attr(C.TRANSFORM,
				C.TRANSLATE + C.OPENPAREN + xTransition + C.CLOSEPAREN);
		graph.stroke.attr(C.TRANSFORM,
				C.TRANSLATE + C.OPENPAREN + xTransition + C.CLOSEPAREN);
	};
};


var HistogramGraph = function(options) {
	MetricGraph.call(this, options);

	var graph = this;

	graph.element.select(".type-symbol")
		.append("img")
			.attr("src", "/pup-histo.png");;

	var stackData = function(metricData) {
		var stack = d3.layout.stack()
				.x(function(d) { return d.time; })
				.y(function(d) { return d.value; })
				.out(function(d, y0, y) {
					d.y0 = y0;
					d.y = d.value;
				});
		var values = metricData.map(function(layer) { return layer.values; })
				.sort(function(a, b) {
					a = a[a.length-1].value;
					b = b[b.length-1].value;
					return a === b ? 0 :
									(a < b) ? 1 : -1;
				});
		return stack(values);
	};

	var height = graph.height,
		data = stackData(graph.metric.data),
		metric = graph.metric;

	graph.path = this.svg.append(C.G)
			.attr("clip-path", function(d, i) {
			   return "url(#clip" + metric.uuid + C.DASH + i + C.CLOSEPAREN;
			})
		.selectAll(C.PATH)
			.data(data)
		.enter().append(C.PATH)
			.attr(C.ID, function(d, i) {
				return C.AREA + metric.uuid + C.DASH + i;
			})
			.attr(C.CLASS, C.AREA)
			.attr(C.D, graph.area);

	graph.stroke = this.svg.append(C.G)
			.attr("clip-path", function(d,i) {
				return "url(#clip" + metric.uuid + C.DASH + i + C.CLOSEPAREN;
			})
		.selectAll(C.PATH)
			.data(data)
		.enter().append(C.PATH)
			.attr(C.ID, function(d, i) {
				return C.LINE + metric.uuid + C.DASH + i;
			})
			.attr(C.CLASS, C.LINE)
			.attr(C.D, graph.line);

	graph.updateLatestVal = function(now) {
		if (metric.timedOut.is || +now - metric.timedOut.at < metric.freq * 2) {
			graph.latest.classed(C.HIDDEN, true);
		} else {
			graph.latest.data(metric.mostRecent).text(function(d, i) {
				return graph.format(d.values.value);
			}).classed(C.HIDDEN, false);
		}
	};

	graph.redraw = function(now) {
		var g_element     = graph.element,
			g_metric      = graph.metric;

		for (var i = 0, len = metric.data.length; i < len; i++) {
			g_element.select(C.HASH + C.AREA + g_metric.uuid + C.DASH + i)
					.attr(C.D, graph.area)
					.attr(C.TRANSFORM, null); // reverts any transition

			g_element.select(C.HASH + C.LINE + g_metric.uuid + C.DASH + i)
					.attr(C.D, graph.line)
					.attr(C.TRANSFORM, null);

			g_element.select(C.HASH + C.TEXT + g_metric.uuid + C.DASH + i).transition().attr(C.TRANSFORM,
				C.TRANSLATE + C.OPENPAREN + (graph.clippedWidth + 4) + C.COMMA + (graph.y(g_metric.mostRecent[i].values.value) + 3) + C.CLOSEPAREN);
		}

		graph.xAxis.call(graph.x.axis);
		graph.yAxis.call(graph.y.axis);

		var xTransition = graph.x(now - (graph.n - 1) * graph.duration);
		for (var _ = 0, len = graph.metric.data.length; _ < len; _++) {
			graph.path.attr(C.TRANSFORM, C.TRANSLATE + C.OPENPAREN + xTransition + C.CLOSEPAREN);
			graph.stroke.attr(C.TRANSFORM, C.TRANSLATE + C.OPENPAREN + xTransition + C.CLOSEPAREN);
		}
	};
};
/* PupController.js
 * Coordinates UI for pup
 *
 * Public interface:
 *	tryStart()		: starts controller if not already created
 *	isRunning()		: accessor returns whether or not the controller is running
 *	n()				: accessor returns number of datapoints
 */

var PupController = function(isWSClosed, Store, $) {
	var minutes		= 10,									// window period
		duration	= Math.sqrt(minutes * 60 * 1000),		// transitions work best if duration and n are close in value
		n			= Math.ceil(duration),					// number of data points
		step		= 0,									// if smooth transitions are enabled, this signifies the lag
		now			= new Date(Date.now() - duration),		// now set to current time minus a transition period
		running		= false,								// determines whether PupController is running
		metrics		= [],									// an array of all the Metric objects
		graphsByName= {},									// an object of all the graph objects, keyed by metric name
		sideByName	= {},									// an object of all the entries objects, keyed by metric name
		format		= d3.format(".2s");						// defines format. rounding to two significant digits.


	var addEntry = function(metric, creationTime) {
		var entry = d3.select("#metric-list")
			.append("li")
				.attr(C.ID, "li" + metric.uuid)
				.attr(C.NAME, metric.name)
				.attr(C.TIME, +creationTime);

		entry.append("span")
				.attr(C.CLASS, "li-metric")
				.text(metric.name);

		entry.append("span")
				.attr(C.CLASS, "li-val");

		sideByName[metric.name] = entry;
	};

	var addGraph = function(metric, creationTime) {
		var container = d3.select("#graphs").append("div")
				.attr(C.ID, metric.name)
				.attr(C.NAME, metric.name)
				.attr(C.TIME, +creationTime)
				.attr(C.CLASS, "plot-box");

		var metricHead = container.append("div")
				.attr(C.CLASS, "metric-head");

		metricHead.append("span")
				.attr(C.CLASS, "type-symbol");

		metricHead.append("h5")
				.attr(C.CLASS, "metric-name")
				.text(metric.name);

		metricHead.append("a")
				.attr("href", metric.name);

		metricHead.append("a")
				.attr(C.CLASS, "csv")
				.attr(C.NAME, metric.name)
				.text("CSV");

		var div = container.append("div")
				.attr(C.CLASS, "plot");

		if (metric.type === "histogram") {
			graphsByName[metric.name] = new HistogramGraph({
				metric	: metric,
				element	: container,
				n		: n,
				duration: duration,
				now		: +now
			});
		} else if (metric.type !== "histogram") {
			graphsByName[metric.name] = new LineGraph({
				metric	: metric,
				element	: container,
				n		: n,
				duration: duration,
				now		: +now
			});
		} // may be more types

		pub.interact().sort().byActive();

		$("#waiting, #no-metrics").addClass("hidden");
		$("#graphs, #data-streaming").removeClass("hidden");
	};

	var clearScreen = function() {
		$('#graphs').empty();
		$('#waiting').addClass("hidden");
		$('#data-streaming').addClass("hidden");
		$('#disconnected').removeClass("hidden");
		$('#listening').html("Not " + $('#listening').html());
		window.scrollTo(0,0);
	};

	var run = function() {
		var interval = setInterval(function() {
			if (isWSClosed()) {
				running = false;
				clearScreen();
				clearTimeout(interval);
			}

			now = new Date();

			metrics = Store.getMetrics();

			var i = metrics.length;
			while (i--) {
				var metric = metrics[i];

				metric.setIfTimedOut(now);

				if (!graphsByName.hasOwnProperty(metric.name)) {
					var creationTime = new Date();
					addEntry(metric, creationTime);
					addGraph(metric, creationTime);
				}

				graph = graphsByName[metric.name];
				graph.updateScales(now);

				if (metric.hasNewData()) {
					metric.pushRecent();
				} else if (metric.timedOut.is) {
					metric.pushNull(new Date());
				}

				graph.tryDrawProgress(now);

				graph.redraw(now);

				var timeWindow = +now - (minutes * 60000 + metric.freq);
				metric.shiftOld(timeWindow);

				graph.updateLatestVal(now);

				if (metric.type === "histogram") {
					sideByName[metric.name].select(".li-val").text(format(metric.average))
						.classed("timed-out", false);
				} else {
					sideByName[metric.name].select(".li-val").text(format(metric.mostRecent[0].value))
						.classed("timed-out", false);
				}

				if (metric.timedOut.is) {
					sideByName[metric.name].select(".li-val").html("♦")
						.classed("timed-out", true);
				}

				if (metric.tags.length) {
					$("#tags").removeClass("hidden");
				}
			}
		}, duration + step + 0.5);
	};

	var pub = {};

	pub.tryStart = function() {
		if (!running) {
			running = true;
			setTimeout(function() {
				run();
			}, 0);
			return 1;
		} else { return 0; }
	};

	pub.interact = function() {
		var graphCount,
			totalGraphCount;

		var showLeft = function() {
			$("#if-more").removeClass("hidden").detach().insertBefore("#by");
			$("#num-more").html(totalGraphCount - graphCount);
			$("#dot").addClass("hidden");
		};

		var downloadCSV = function(metric) {
			var CSVWindow = window.open();
			CSVWindow.document.title = metric.name;
			var csv = metric.toCSV();
			CSVWindow.document.write(csv);
			CSVWindow.document.body.style.fontFamily = "monospace";
		};

		var intPub = {};

		intPub.updatePlotCount = function() {
			var graphDivs	= document.getElementById('graphs').children,
				shownCount	= 0;

			$(graphDivs).each(function() {
				if ( $(this).is(':visible') ) {
					shownCount++;
				}
			});

			graphCount		= shownCount;
			totalGraphCount	= graphDivs.length;
		};

		intPub.filterBy = function(term) {
			var graphDivs	= document.getElementById('graphs').children,
				entryLis	= document.getElementById('metric-list').children,
				lowerTerm	= term.toLowerCase(),
				i			= graphDivs.length;

			while (i--) {
				var id		= graphDivs[i].id,
					lowerId	= id.toLowerCase(),
					re		= new RegExp(lowerTerm, 'gi');
				if (lowerId.match(re)) {
					graphDivs[i].style.display = "";
					entryLis[i].style.display = "";
				} else {
					graphDivs[i].style.display = "none";
					entryLis[i].style.display = "none";
				}
			}

			intPub.updatePlotCount();
			if (graphCount < totalGraphCount) {
				showLeft();
			} else {
				$("#if-more").addClass("hidden");
				$("#dot").removeClass("hidden");
			}
		};

		intPub.sort = function() {
			var graphsRoot			= document.getElementById('graphs'),
				graphsRootChildren	= graphsRoot.children,
				entriesRoot			= document.getElementById('metric-list'),
				entriesRootChildren	= entriesRoot.children,
				graphsArray			= [],
				entriesArray		= [],
				i					= graphsRootChildren.length;

			var loadArrays = function() {
				var j = 0;
				while (j < i) {
					graphsArray[graphsArray.length] = graphsRootChildren[j];
					entriesArray[graphsArray.length] = entriesRootChildren[j];
					j++;
				}
			};

			var emptyArrays = function() {
				graphsArray.length = 0;
				entriesArray.length = 0;
			};

			var appendSortedArrays = function() {
				for (var j = 0; j < i; j++) {
					graphsRoot.appendChild(graphsArray[j]);
					entriesRoot.appendChild(entriesArray[j]);
				}
			};

			var byName = function(array) {
				return array.sort(function(a, b) {
					a = a.getAttribute(C.NAME).toLowerCase();
					b = b.getAttribute(C.NAME).toLowerCase();
					return a === b ? 0
									: (a < b) ? -1 : 1;
				});
			};

			var byTimeAdded = function(array) {
				return array.sort(function(a, b) {
					a = parseInt(a.getAttribute(C.TIME), 10);
					b = parseInt(b.getAttribute(C.TIME), 10);
					return a === b ? 0
									: (a < b) ? -1: 1;
				});
			};

			var sortPub = {};

			sortPub.byName = function() {
				loadArrays();
				graphsArray = byName(graphsArray);
				entriesArray = byName(entriesArray);
				appendSortedArrays();
				emptyArrays();
			};

			sortPub.byTimeAdded = function() {
				loadArrays();
				graphsArray = byTimeAdded(graphsArray);
				entriesArray = byTimeAdded(entriesArray);
				appendSortedArrays();
				emptyArrays();
			};

			sortPub.byActive = function() {
				var active = $(".sort-active")[0].getAttribute(C.ID);
				if (active === "by-name") {
					sortPub.byName();
				} else { sortPub.byTimeAdded(); }
			};

			return sortPub;
		};

		intPub.filterByTags = function(t) {
			var graphDivs		= document.getElementById('graphs').children,
				entries			= document.getElementById('metric-list').children,
				tags			= document.getElementById('tag-list').children,
				i				= graphDivs.length,
				tagSelected		= t[0],
				key;

			if ($(tagSelected).hasClass("tag-active")) {
				$(tagSelected).removeClass("tag-active");

				$(".graph-tag").each(function() {
					if ($(this).html() === $(tagSelected).html()) {
						$(this).css("color", "#999");
					}
				});

				var activeTags = [];
				for (var j = 0, len = tags.length; j < len; j++) {
					if ($(tags[j]).hasClass("tag-active")) {
						activeTags[activeTags.length] = tags[j].getAttribute("tag");
					}
				}

				while (i--) {
					key = graphDivs[i].getAttribute(C.NAME);
					var graphTags =	Store.getMetricByName(key).tags,
						k = activeTags.length;

					if (!activeTags.length) {
						graphDivs[i].style.display = "";
						entries[i].style.display = "";
					} else {
						while (k--) {
							if (graphTags.indexOf(activeTags[k]) > -1) { break; }
						}

						if (!k) {
							graphDivs[i].style.display = "";
							entries[i].style.display = "";
						}
					}
				}

				var query = $("#query").val();
				if (query.length) { intPub.filterBy(query); }

				intPub.updatePlotCount();
				if (graphCount < totalGraphCount) {
					showLeft();
				} else {
					$("#if-more").addClass("hidden");
					$("#dot").removeClass("hidden");
				}
			} else {
				$(tagSelected).addClass("tag-active");

				$(".graph-tag").each(function() {
					if ($(this).html() === $(tagSelected).html()) {
						$(this).css("color", "#6f56a2");
					}
				});

				while (i--) {
					key = graphDivs[i].getAttribute(C.NAME);

					if (-1 === Store.getMetricByName(key).tags.indexOf(tagSelected.getAttribute("tag"))) {
						graphDivs[i].style.display = "none";
						entries[i].style.display = "none";
					}
				}

				intPub.updatePlotCount();
				if (graphCount < totalGraphCount) {
					showLeft();
				}
			}
			return intPub;
		};

		intPub.highlightGraph = function(metricName) {
			var graph = $(".plot-box[name=\"" + metricName + '\"]');
			var graphHeader = $(graph).find('h5');
			$(graphHeader).addClass("highlight-graph-header");
			$(graph).addClass("highlight-graph");
			var entry = $('li[name=\"' + metricName + '\"]');
			$(entry).addClass("highlight-metric");
			return intPub;
		};

		intPub.scrollToGraph = function(metricName) {
			var graph = $('.plot-box[name=\"' + metricName + '\"]');
			var y = $(graph).offset().top;
			window.scrollTo(0, y - 15);
			return intPub;
		};

		intPub.fadeGraph = function(metricName) {
			var graph = $(".plot-box[name=\"" + metricName + '\"]');
			var graphHeader = $(graph).find('h5');
			$(graphHeader).removeClass("highlight-graph-header");
			$(graph).removeClass("highlight-graph");
			var entry = $('li[name=\"' + metricName + '\"]');
			$(entry).removeClass("highlight-metric");
			return intPub;
		};

		intPub.downloadCSV = function(name) {
			var metric = Store.getMetricByName(name);
			downloadCSV(metric);
		};

		return intPub;
	};

	pub.n = function() { return n; };

	return pub;
}(PupSocket.isClosed, Store, $);
