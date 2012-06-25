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

	// create and initialize scales
	this.x = d3.time.scale()
			.domain([then, now])
			.range([0, width]);

	this.y = d3.scale.linear()
			.range([height, 0]);

	var x = this.x,
		y = this.y;

	// graph-specific format
	this.format = d3.format(".2s");

	// create svg
	this.svg = this.element.select(".plot")
		.append("svg")
			.attr("width", width + margin.left + margin.right)
			.attr("height", height + margin.top + margin.bottom)
			.style("margin-left", -margin.left + 10 + "px")
		.append("g")
			.attr("transform", "translate(" + margin.left + ", " + margin.top + ")");

	// configure axes
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

	// configure line generator
	this.line = d3.svg.area()
		.interpolate("linear")
		.x(function(d) { return x(d.time); })
		.y0(function(d) { return height; })
		.y1(function(d) { return y(d.value); });

	// add clipPath	
	this.svg.append("defs").append("clipPath")
			.attr("id", "clip" + this.metric.uuid)
		.append("rect")
			.attr("width", width)
			.attr("height", height);

	// initialize latest value for the graph
	this.latest = this.element.select(".latest-val")
		.text("");

	// graph tags
	this.element.append("ul")
			.attr("class", "graph-tags")
			.text("tags: ")
		.selectAll("li")
			.data(this.metric.tags)
		.enter().append("li")
			.attr("class", "graph-tag")
			.attr("tag", function(d) { return d; })
			.text(function(d) { return d; });

	// adds to tag list if there are more tags
	d3.select("#tag-list").selectAll("li")
			.data(allTags)
		.enter().append("li")
			.attr("tag", function(d) { return d; })
			.attr("class", "tag")
			.text(function(d) { return d; });

	// updates scales
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
