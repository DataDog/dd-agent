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
															// 	duration represents the buffer time window for transitions
		n 			= Math.ceil(duration),					// number of data points
		step		= 0,									// if smooth transitions are enabled, this signifies the lag
		timeout		= 10 * 1000,							// timeout a metric after this many milliseconds
		now			= new Date(Date.now() - duration),		// now set to current time minus a transition period
		running		= false,								// determines whether PupController is running
		metrics		= [],									// an array of all the Metric objects
		graphsByName= {},									// an object of all the graph objects, keyed by metric name
		sideByName 	= {},									// an object of all the entries objects, keyed by metric name
		format 		= d3.format(".2s");						// defines format. rounding to two significant digits.

	// private helpers --------------------------------------------------

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

		//sort by the active sorting filter
		pub.interact().sort().byActive();

		// remove the directions and show graphs
		$("#waiting, #no-metrics").addClass("hidden");
		$("#graphs, #data-streaming").removeClass("hidden");
	};

	var clearScreen = function() {
		$('#graphs').empty();
		$('#data-streaming').addClass("hidden");
		$('#disconnected').removeClass("hidden");
		$('#listening').html("Not " + $('#listening').html());
	};

	// TODO: Make histogram most recent value the average.
	var updateSidebar = function(metric) {
		if (metric.type === "histogram")
			sideByName[metric.name].select(".li-val").text("NA");
		else {
			sideByName[metric.name].select(".li-val").text(format(metric.mostRecent.value));
		}
	};
	
	var run = function() {
		var interval = setInterval(function() {
			// check if connection closed				
			if (isWSClosed()) { 
				running = false;
				clearScreen();
				clearTimeout(interval);
			}

			now = new Date();

			// fetch metrics
			metrics = Store.getMetrics();

			for (var i = 0; i < metrics.length; i++) {
				var metric = metrics[i],
					graph = graphsByName[metric.name],
					timedOut = metric.isTimedOut(now, timeout);

				// if graph doesn't exist, create it
				if (undefined == graph) {
					addEntry(metric);
					addGraph(metric);
					graph = graphsByName[metric.name];
				} 	

				graph.updateScales(now);
				
				// push most recent data point on	
				metric.pushRecent(timedOut, now);	
				
				// redraw the graph
				graph.redraw(now);

				// shift off the old
				metric.shiftOld();

				// update entry
				graph.updateLatestVal();

				// update sidebar
				updateSidebar(metric);
			}
		}, duration + step + 0.5);
	};

	// public interface --------------------------------------------------
	pub = {};

	// attempt to start the controller if it isn't running.
	pub.tryStart = function() {
		if (!running) {
			running = true;
			setTimeout(function() {
				run();
			}, 0);
			return 1;
		} else { return 0; }	
	};

	// interaction interface
	pub.interact = function() {
		var graphCount,
			totalGraphCount;

		var showLeft = function() {
			$("#if-more").removeClass("hidden").detach().appendTo("#content");
			$("#num-more").html(totalGraphCount - graphCount);
			$("#dot").addClass("hidden");
		}
		
		// interact public interface -----------------------------------------
		intPub = {};

		// internally updates plot counts	
		intPub.updatePlotCount = function() {
			var graphDivs 	= document.getElementById('graphs').children,
				shownCount 	= 0;

			// TODO: Strip out jQuery
			$(graphDivs).each(function() {
				if ( $(this).is(':visible') ) {
					shownCount++;
				}
			});
			
			graphCount		= shownCount;
			totalGraphCount	= graphDivs.length;
		}

		// filter graphs and their corresponding sidebar entries by term
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

		// sorting interface
		intPub.sort = function() {
			var graphsRoot 			= document.getElementById('graphs'),
				graphsRootChildren 	= graphsRoot.children,
				entriesRoot			= document.getElementById('metric-list'),
				entriesRootChildren = entriesRoot.children,
				graphsArray			= [],
				entriesArray		= [],
				i 					= graphsRootChildren.length;

			// private sorting helpers -------------------------------------
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

			// sort public interface ---------------------------------------	
			sortPub = {};

			// sort graphs and entries by their names, descending
			sortPub.byName = function() {
				loadArrays();
				graphsArray = byName(graphsArray);
				entriesArray = byName(entriesArray);
				appendSortedArrays();	
				emptyArrays();
			};

			// sort graphs and entries by the time they were added
			sortPub.byTimeAdded = function() {
				loadArrays();
				graphsArray = byTimeAdded(graphsArray);
				entriesArray = byTimeAdded(entriesArray);
				appendSortedArrays();
				emptyArrays();
			};

			// find which is active
			sortPub.byActive = function() {
				var active = $(".active")[0].getAttribute("id");
				if (active === "by-name") {
					sortPub.byName();
				} else { sortPub.byTimeAdded(); }
			};

			return sortPub;
		}
		
		// filter shown metrics by active tags
		intPub.filterByTags = function(t) {
			var graphDivs		= document.getElementById('graphs').children,
				entries			= document.getElementById('metric-list').children,
				tags 			= document.getElementById('tag-list').children,
				i 				= graphDivs.length,
				tagSelected		= t[0],
				key;	

			if ($(tagSelected).hasClass("tag-active")) {
				$(tagSelected).removeClass("tag-active");

				// remove highlighted graph tags
				$(".graph-tag").each(function() {
					if ($(this).html() === $(tagSelected).html()) {
						$(this).css("color", "#999");
					}
				});

				// get active tags
				var activeTags = [];
				for (var j = 0; j < tags.length; j++) {
					if ($(tags[j]).hasClass("tag-active")) {
						activeTags.push(tags[j].getAttribute("tag"));
					}
				}

				// for each plot
				while (i--) {
					key = graphDivs[i].getAttribute("name");
					var graphTags =	Store.getMetricByName(key).tags,
						j = activeTags.length;

					// if no tags are selected, show all
					if (!activeTags.length) {
						graphDivs[i].style.display = "";
						entries[i].style.display = "";
					} else {
						// else, check if current graph's tags match active tags
						while (j--) {
							if (graphTags.indexOf(activeTags[j]) > -1) { break; }
						}
				
						// if current graph's tags match active tags, show them
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

				// add highlighted graph tags
				$(".graph-tag").each(function() {
					if ($(this).html() === $(tagSelected).html()) {
						$(this).css("color", "#6f56a2");
					}
				});

				while (i--) {
					key = graphDivs[i].getAttribute("name");

					// hide those plots that don't match the tag just selected
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

		// highlights graph
		intPub.highlightGraph = function(metricName) {
			var graph = $('.plot-box[name=' + metricName + '] h5');
			$(graph).css("background-color", "#EADFF5");
			var entry = $('.li[name=' + metricName + ']');
			$(entry).css("background-color", "#EADFF5");
			return intPub;
		};

		// scroll to the graph just clicked on in the entries list
		intPub.scrollToGraph = function(metricName) {
			var graph = $('.plot-box[name=' + metricName + ']');
			var y = $(graph).offset().top;
			window.scrollTo(0, y);
			return intPub;
		};

		// fade the graph when the mouse leaves the entry
		intPub.fadeGraph = function(metricName) {
			var graph = $('.plot-box[name=' + metricName + '] h5');
			$(graph).animate({'backgroundColor': "white"}, 200);
			var entry = $('.li[name=' + metricName + ']');
			$(entry).animate({'backgroundColor': "transparent"}, 200);
			return intPub;
		};

		return intPub;
	}

	// accessor for the number of datapoints in each graph
	pub.n = function() { return n; };

	return pub;
}(PupSocket.isClosed, Store, $);
