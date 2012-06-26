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

	for (var i = 0; i < this.tags.length; i++) {
		var tag = this.tags[i];
		if (-1 === allTags.indexOf(tag)) {
			allTags.push(tag);					// used for tag filtering
		}
	}
};


function Histogram(options) {
	Metric.call(this, options);

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

	var verify = function(incoming) {
		if ("Waiting" in incoming) {
			return false;
		}

		return true;
	}

	pub = {};

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

	pub.getMetrics = function() {
		var metrics = [];
		for (var metric in metricsByName) metrics.push(metricsByName[metric]);
		return metrics;
	}

	pub.getMetricByName = function(name) {
		return metricsByName[name];
	}

	return pub;
}();
/* PupSocket.js
 * Abstraction for WebSocket.
 * Creates WebSocket connection and redirects incoming data to storage.
 *
 * Public interface:
 * 	tryStart() 		: creates WebSocket connection if unestablished.
 * 	isEstablished() : returns a boolean value representing whether a WebSocket
 * 					  connection was tried and established.
 * 	isClosed() 		: returns a boolean value representing whether the WebSocket
 * 					  connection was closed.
 */

var PupSocket = function(port, save) {
	var connEstablished = false,
		closed = false;

	pub = {};

	pub.isEstablished = function() {
		return true === connEstablished;
	}

	pub.tryStart = function(port) {
		if (this.isEstablished()) return;
		var ws = new WebSocket("ws://localhost:" + port + "/pupsocket"),
			connEstablished = true;

		ws.onmessage = function(evt) {
			var incoming;
			try { incoming = JSON.parse(evt.data); }
			catch (err) {
				throw "There was an error parsing the incoming data: " + err;
			}

			var attempt = save(incoming);
			switch(attempt) {
				case 0:
					break;
				case 1:
					throw "Malformed data sent to client"
					break;
				case 2:
					var hitLimit = document.getElementById("limit-error");
					hitLimit.innerHTML = "You have reached the graph count limit";
					setTimeout(function() {
						hitLimit.innerHTML = "";
					}, 5000);
					break;
			}
		};

		ws.onclose = function() {
			closed = true;
		};

		ws.onerror = function() {
			connEstablished = false;
		}

		return pub;
	}

	pub.isClosed = function() { return closed; }

	return pub;
}(port, Store.save);
/* MetricGraph.js
 * Defines how a metric visual is plotted and represented in the side bar. The graphic counterpart
 * to Metric, which solely represents a metric data structure.
 */

var MetricGraph = function(options) {

/*
	noww - n * duration         	  now - duration      now
	|---------------------------------|--------------------|
				  VISIBLE                   INVISIBLE

	Having new points append in the invisible section allows
	the transitions to appear smoothly and not jerky.
*/


	var margin 		= {top: 10, right: 0, bottom: 26, left: 45},
		width 		= 400 - margin.right,
		height 		= 140 - margin.top - margin.bottom,
		yBuffer	 	= 1.3;

	this.n 			= options.n;
	this.duration 	= options.duration;
	this.metric 	= options.metric;
	this.element 	= options.element;
	this.height 	= height;
	this.width 		= width;
	this.baseColor 	= d3.interpolateRgb("#6f56a2", "#EADFF5");

	var then 		= options.now - (this.n - 2) * this.duration,
		now			= options.now - this.duration;

	this.x = d3.time.scale()
			.domain([then, now])
			.range([0, width]);

	this.y = d3.scale.linear()
			.range([height, 0]);

	var x = this.x,
		y = this.y;

	this.format = d3.format(".2s");

	this.svg = this.element.select(".plot")
		.append("svg")
			.attr("width", width + margin.left + margin.right)
			.attr("height", height + margin.top + margin.bottom)
			.style("margin-left", -margin.left + 10 + "px")
		.append("g")
			.attr("transform", "translate(" + margin.left + ", " + margin.top + ")");

	this.xAxis = this.svg.append("g")
			.attr("class", "x axis")
			.attr("transform", "translate(0, " + height + ")")
			.call(this.x.axis = d3.svg.axis().scale(this.x)
										.orient("bottom")
										.ticks(5)
										.tickSize(-height)
										.tickPadding(4)
										.tickSubdivide(true));

	this.yAxis = this.svg.append("g")
			.attr("class", "y axis")
			.call(this.y.axis = d3.svg.axis().scale(this.y)
										.orient("left")
										.ticks(5)
										.tickFormat(this.format));

	this.line = d3.svg.area()
		.interpolate("linear")
		.x(function(d) { return x(d.time); })
		.y0(function(d) { return height; })
		.y1(function(d) { return y(d.value); });

	this.svg.append("defs").append("clipPath")
			.attr("id", "clip" + this.metric.uuid)
		.append("rect")
			.attr("width", width)
			.attr("height", height);

	this.latest = this.element.select(".latest-val")
		.text("");

	this.element.append("ul")
			.attr("class", "graph-tags")
			.text("tags: ")
		.selectAll("li")
			.data(this.metric.tags)
		.enter().append("li")
			.attr("class", "graph-tag")
			.attr("tag", function(d) { return d; })
			.text(function(d) { return d; });

	d3.select("#tag-list").selectAll("li")
			.data(allTags)
		.enter().append("li")
			.attr("tag", function(d) { return d; })
			.attr("class", "tag")
			.text(function(d) { return d; });

	this.updateScales = function(now) {
		this.x.domain([now - (this.n - 2) * this.duration, now - this.duration]);
		this.y.domain([0, yBuffer * this.metric.max]);
	}

}



var LineGraph = function(options) {
	MetricGraph.call(this, options);

	var color = this.baseColor,
		path = this.svg.append("g")
			.attr("clip-path", "url(#clip" + this.metric.uuid + ")")
		.append("path")
			.data([this.metric.data])
			.attr("class", "line")
			.attr("id", "line" + this.metric.uuid)
			.attr("d", this.line)
			.style("fill", function(d, i) { return color((i % 5)/5); })
			.style("stroke", "#3B226E");

	this.updateLatestVal = function() {
		this.latest.text(this.format(this.metric.mostRecent.value));
	}

	this.redraw = function(now) {
		d3.select("#line" + this.metric.uuid)
				.attr("d", this.line)
				.attr("transform", null); // reverts any transition

		this.xAxis.call(this.x.axis);

		this.yAxis.transition()
				.duration(100)
				.ease("linear")
				.call(this.y.axis);

		path.attr("transform", "translate(" + this.x(now - (this.n - 1) * this.duration) + ")");
	};
};


var HistogramGraph = function(options) {
	MetricGraph.call(this, options);

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
		return stack(values); // TODO: Handle ordering better.
	}

	var height = this.height,
		color = this.baseColor,
		data = stackData(this.metric.data),
		metric = this.metric,
		path = this.svg.append("g")
			.attr("clip-path", "url(#clip" + this.metric.uuid + ")")
		.selectAll("path")
			.data(data)
		.enter().append("path")
			.attr("id", function(d, i) {
				return "line" + metric.uuid + "-" + i; })
			.attr("class", "line")
			.style("fill", function(d, i) {
				return color(1-(i % 3)/3);
			})
			.style("stroke", "3B226E")
			.attr("d", this.line);

	this.updateLatestVal = function() {
		this.latest.text("NA");
	}

	this.redraw	= function(now) {
		for (var i = 0; i < this.metric.data.length; i++) {
			d3.select("#line" + this.metric.uuid + "-" + i)
					.attr("d", this.line)
					.attr("transform", null); // reverts any transition
		}

		this.xAxis.call(this.x.axis);
		this.yAxis.transition()
				.duration(100)
				.ease("linear")
				.call(this.y.axis);

		for (var i = 0; i < this.metric.data.length; i++) {
			path.attr("transform", "translate(" + this.x(now - (this.n - 1) * this.duration) + ")");
		}
	}
};
/* PupController.js
 * Coordinates UI for pup
 *
 * Public interface:
 * 	tryStart()		: starts controller if not already created
 *	isRunning()		: accessor returns whether or not PupController is running
 *
 */

var PupController = function(isWSClosed, Store, $) {
	var minutes		= 4,									// window period
		duration 	= Math.sqrt(minutes * 60 * 1000),		// transitions work best if duration and n are close in value
		n 			= Math.ceil(duration),					// number of data points
		step		= 0,									// if smooth transitions are enabled, this signifies the lag
		timeout		= 10 * 1000,							// timeout a metric after this many milliseconds
		now			= new Date(Date.now() - duration),		// now set to current time minus a transition period
		running		= false,								// determines whether PupController is running
		metrics		= [],									// an array of all the Metric objects
		graphsByName= {},									// an object of all the graph objects, keyed by metric name
		sideByName 	= {},									// an object of all the entries objects, keyed by metric name
		format 		= d3.format(".2s");						// defines format. rounding to two significant digits.


	var addEntry = function(metric) {
		var entry = d3.select("#metric-list")
			.append("li")
				.attr("id", "li" + metric.uuid)
				.attr("name", metric.name)
				.attr("time", +metric.createdAt)
				.attr("class", metric.type);

		entry.append("span")
				.attr("class", "li-metric")
				.attr("x", 3)
				.attr("y", 12)
				.text(metric.name);

		entry.append("span")
				.attr("class", "li-val")
				.attr("x", 150)
				.attr("y", 12)
				.text("");

		$(entry[0]).hide().fadeIn(500);

		sideByName[metric.name] = entry;
	};

	var addGraph = function(metric) {
		var container = d3.select("#graphs").append("div")
				.attr("id", metric.name)
				.attr("name", metric.name)
				.attr("time", +metric.createdAt)
				.attr("class", "plot-box");

		var metricHead = container.append("div")
				.attr("class", "metric-head")

		metricHead.append("span")
				.attr("class", "latest-val")

		metricHead.append("h5")
				.attr("class", "metric-name")
				.text(metric.name)

		metricHead.append("a")
				.attr("href", metric.name);

		metricHead.append("span")
				.attr("class", "download")
				.text("download");

		var div = container.append("div")
				.attr("class", "plot")

		if (metric.type === "histogram") {
			graphsByName[metric.name] = new HistogramGraph({
				metric 	: metric,
				element : container,
				n 		: n,
				duration: duration,
				now 	: +now
			});
		} else if (metric.type !== "histogram") {
			graphsByName[metric.name] = new LineGraph({
				metric 	: metric,
				element : container,
				n 		: n,
				duration: duration,
				now 	: +now
			});
		} // may be more types

		pub.interact().sort().byActive();

		$("#waiting, #no-metrics").addClass("hidden");
		$("#graphs, #data-streaming").removeClass("hidden");
	};

	var clearScreen = function() {
		$('#graphs').empty();
		$('#data-streaming').addClass("hidden");
		$('#disconnected').removeClass("hidden");
		$('#listening').html("Not " + $('#listening').html());
	};

	var updateSidebar = function(metric) {
		if (metric.type === "histogram")
			sideByName[metric.name].select(".li-val").text("NA");
		else {
			sideByName[metric.name].select(".li-val").text(format(metric.mostRecent.value));
		}
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

			for (var i = 0; i < metrics.length; i++) {
				var metric = metrics[i],
					graph = graphsByName[metric.name],
					timedOut = metric.isTimedOut(now, timeout);

				if (undefined == graph) {
					addEntry(metric);
					addGraph(metric);
					graph = graphsByName[metric.name];
				}

				graph.updateScales(now);

				metric.pushRecent(timedOut, now);

				graph.redraw(now);

				metric.shiftOld();

				graph.updateLatestVal();

				updateSidebar(metric);
			}
		}, duration + step + 0.5);
	};

	pub = {};

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
			$("#if-more").removeClass("hidden").detach().appendTo("#content");
			$("#num-more").html(totalGraphCount - graphCount);
			$("#dot").addClass("hidden");
		}

		intPub = {};

		intPub.updatePlotCount = function() {
			var graphDivs 	= document.getElementById('graphs').children,
				shownCount 	= 0;

			$(graphDivs).each(function() {
				if ( $(this).is(':visible') ) {
					shownCount++;
				}
			});

			graphCount		= shownCount;
			totalGraphCount	= graphDivs.length;
		}

		intPub.filterBy = function(term) {
			var graphDivs 	= document.getElementById('graphs').children,
				entryLis	= document.getElementById('metric-list').children,
				lowerTerm 	= term.toLowerCase(),
				i 			= graphDivs.length;

			while (i--) {
				var id		= graphDivs[i].id,
					lowerId	= id.toLowerCase(),
					re 		= new RegExp(lowerTerm, 'gi');
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
		}

		intPub.sort = function() {
			var graphsRoot 			= document.getElementById('graphs'),
				graphsRootChildren 	= graphsRoot.children,
				entriesRoot			= document.getElementById('metric-list'),
				entriesRootChildren = entriesRoot.children,
				graphsArray			= [],
				entriesArray		= [],
				i 					= graphsRootChildren.length;

			var loadArrays = function() {
				var j = 0;
				while (j < i) {
					graphsArray.push(graphsRootChildren[j]);
					entriesArray.push(entriesRootChildren[j]);
					j++;
				}
			};

			var emptyArrays = function() {
				graphsArray.length = 0;
				entriesArray.length = 0;
			}

			var appendSortedArrays = function() {
				for (var j = 0; j < i; j++) {
					graphsRoot.appendChild(graphsArray[j]);
					entriesRoot.appendChild(entriesArray[j]);
				}
			};

			var byName = function(array) {
				console.log(array);
				return array.sort(function(a, b) {
					a = a.getAttribute("name");
					b = b.getAttribute("name");
					return a === b ? 0
									: (a < b) ? -1 : 1;
				});
			};

			var byTimeAdded = function(array) {
				return array.sort(function(a, b) {
					a = parseInt(a.getAttribute("time"));
					b = parseInt(b.getAttribute("time"));
					return a === b ? 0
									: (a < b) ? -1: 1;
				});
			};

			sortPub = {};

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
				var active = $(".active")[0].getAttribute("id");
				if (active === "by-name") {
					sortPub.byName();
				} else { sortPub.byTimeAdded(); }
			};

			return sortPub;
		}

		intPub.filterByTags = function(t) {
			var graphDivs		= document.getElementById('graphs').children,
				entries			= document.getElementById('metric-list').children,
				tags 			= document.getElementById('tag-list').children,
				i 				= graphDivs.length,
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
				for (var j = 0; j < tags.length; j++) {
					if ($(tags[j]).hasClass("tag-active")) {
						activeTags.push(tags[j].getAttribute("tag"));
					}
				}

				while (i--) {
					key = graphDivs[i].getAttribute("name");
					var graphTags =	Store.getMetricByName(key).tags,
						j = activeTags.length;

					if (!activeTags.length) {
						graphDivs[i].style.display = "";
						entries[i].style.display = "";
					} else {
						while (j--) {
							if (graphTags.indexOf(activeTags[j]) > -1) { break; }
						}

						if (!j) {
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
					key = graphDivs[i].getAttribute("name");

					if (-1 === Store.getMetricByName(key).tags.indexOf(tagSelected.getAttribute("tag"))) {
						graphDivs[i].style.display = "none";
						entries[i].style.display = "none";
					}
				}

				intPub.updatePlotCount();
				showLeft();
			}
			return intPub;
		};

		intPub.highlightGraph = function(metricName) {
			var graph = $('.plot-box[name=' + metricName + '] h5');
			$(graph).css("background-color", "#EADFF5");
			var entry = $('.li[name=' + metricName + ']');
			$(entry).css("background-color", "#EADFF5");
			return intPub;
		};

		intPub.scrollToGraph = function(metricName) {
			var graph = $('.plot-box[name=' + metricName + ']');
			var y = $(graph).offset().top;
			window.scrollTo(0, y);
			return intPub;
		};

		intPub.fadeGraph = function(metricName) {
			var graph = $('.plot-box[name=' + metricName + '] h5');
			$(graph).animate({'backgroundColor': "white"}, 200);
			var entry = $('.li[name=' + metricName + ']');
			$(entry).animate({'backgroundColor': "transparent"}, 200);
			return intPub;
		};

		return intPub;
	}

	pub.n = function() { return n; };

	return pub;
}(PupSocket.isClosed, Store, $);
