/* MetricGraph.js
 * Defines how a metric visual is plotted and represented in the side bar. The graphic counterpart
 * to Metric, which solely represents a metric data structure.
 *
 * See Constants.js for "C" properties. They are strings meant to avoid static string creation
 * on every iteration.
 */

var MetricGraph = function(options) {

/*
 *  now - n * duration          now - duration          now
    |---------------------------------|--------------------|
                VISIBLE                 INVISIBLE
                                          
    Having new points append in the invisible section allows
    the transitions to appear smoothly and not jerky.
*/


    var margin      = {top: 10, right: 24, bottom: 18, left: 45},
        latestBuff  = 10,
        width       = 470 - margin.right,
        height      = 140 - margin.top - margin.bottom,
        yBuffer     = 1.3;

    this.n          = options.n;
    this.duration   = options.duration;
    this.metric     = options.metric;
    this.element    = options.element;
    this.height     = height;
    this.width      = width;
    this.finishedProgress = false;

    var then        = options.now - (this.n - 2) * this.duration,
        now         = options.now - this.duration,
        interpolation = "basis",
        metric      = this.metric;

    // create and initialize scales
    this.x = d3.time.scale()
            .domain([then, now])
            .range([0, width]);

    this.y = d3.scale.linear()
            .range([height, 0]);

    var x = this.x,
        y = this.y;

    // graph-specific format
    this.format = d3.format(".3s");

    // create svg
    this.svg = this.element.select(".plot")
        .append("svg")
            .attr(C.WIDTH, width + margin.left + margin.right + latestBuff)
            .attr(C.HEIGHT, height + margin.top + margin.bottom)
        .append(C.G)
            .attr(C.WIDTH, width + margin.left - margin.right)
            .attr(C.TRANSFORM, C.TRANSLATE + C.OPENPAREN + margin.left + C.COMMA + margin.top + C.CLOSEPAREN);

    // configure axes
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

    // avoids awkward on-the-pixel-divider issues   
    var ANTIALIAS = 0.5;

    // configure the line   
    this.line = d3.svg.line()
        .interpolate(interpolation)
        .defined(function(d) { return d.value != null; })
        .x(function(d) { return x(d.time) + ANTIALIAS; })
        .y(function(d) { return y(d.value) + ANTIALIAS; });

    // configure line generator
    this.area = d3.svg.area()
        .interpolate(interpolation)
        .defined(this.line.defined())
        .x(this.line.x())
        .y0(function(d) { return height; })
        .y1(this.line.y());

    // clipped so transitions occur smoothly
    this.clippedWidth = x(now - metric.freq);
    
    // add clipPath 
    this.svg.append("defs").append("clipPath")
            .attr(C.ID, function(d,i) {
               return "clip" + metric.uuid + C.DASH + i;
            })
        .append("rect")
            .attr(C.WIDTH, this.clippedWidth)
            .attr(C.HEIGHT, height);

    // latest value
    this.latest = this.svg.selectAll("text.label")
            .data(metric.mostRecent)
        .enter().append("text")
            .attr(C.CLASS, "latest-val")
            .attr(C.ID, function(d, i) {
                return C.TEXT + metric.uuid + C.DASH + i;
            })
            .attr(C.TRANSFORM, C.TRANSLATE + C.OPENPAREN + this.clippedWidth + C.COMMA + height + C.CLOSEPAREN);

    // add loading bar
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

    // graph tags
    this.element.append("ul")
            .attr(C.CLASS, "graph-tags")
            .text("tags: ")
        .selectAll("li")
            .data(metric.tags)
        .enter().append("li")
            .attr(C.CLASS, "graph-tag")
            .attr("tag", function(d) { return d; })
            .text(function(d) { return d; });

    // adds to tag list if there are more tags
    d3.select("#tag-list").selectAll("li")
            .data(allTags)
        .enter().append("li")
            .attr("tag", function(d) { return d; })
            .attr(C.CLASS, "tag")
            .text(function(d) { return d; });

    // updates scales
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
            // multiply freq by 2 to allow for the extra control points
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
