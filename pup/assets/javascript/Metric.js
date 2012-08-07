/* Metric.js
 * Defines Metric data objects, such as Line and Histogram.
 *
 *  updateMostRecent()      : updates the Metric's mostRecent object
 *  pushRecent()            : pushes the Metric's mostRecent object onto data
 *  shiftOld()              : shifts off the Metric's oldest datapoint
 *  isTimedOut()            : returns whether a metric has timed out
 */

// global variables non-specific to any instance of a metric
var allTags = [],
    metricId = 0;

var PupController;
var Metric = function(options) {
    this.n          = PupController.n();        // defines number of datapoints in a graph
    this.createdAt  = new Date();               // creation timestamp. used in sorting by time added
    this.uuid       = metricId++;               // used in selection.
    this.name       = options.metric;           // name of metric. used for sorting by name
    this.type       = options.type;             // type of metric
    this.freq       = options.freq * 1000;      // estimated frequency of sending in milliseconds
    this.tags       = options.tags;             // tags. used for listing tags
    this.max        = 0.0;                      // maximum value. used for determining the y range
    this.data       = [];                       // data series for a metric
    this.timedOut   = {at: +options.now, is: false};                    // if timedOut

    for (var i = 0; i < this.tags.length; i++) {
        var tag = this.tags[i];
        if (-1 === allTags.indexOf(tag)) {
            allTags[allTags.length] = (tag);                    // used for tag filtering
        }
    }
};

// Histogram -----------------------------------------------------------
function Histogram(options) {
    Metric.call(this, options);

    // allow access from a closure  
    var n = this.n;

    this.data = d3.range(options.points.length).map(function(d, i) {
        return {
            "name"      : options.points[i].stackName,
            "values"    : [{"time": +options.now, "value": null}]
        };
    });

    this.mostRecent = options.points.map(function(stk) {
        return {
            "name"      : stk.stackName,
            "values"    : {time: +options.now, value: null}
        };
    }); 
}

Histogram.prototype.updateMostRecent = function(incomingMetric, metric) {
    var max = this.max;
    var average = this.average;
    this.mostRecent = incomingMetric.points.map(function(stk) {
        return {
            "name"      : stk.stackName,
            "values"    : stk.values.map(function(d) {
                if (d[1] > max) { max = d[1]; }
                if (stk.stackName === "avg") { average = d[1]; }
                return {
                    "time"  : d[0] * 1000,
                    "value" : d[1]
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
            // headers
            for (var stkI = 0, stackCount = this.data.length; stkI < stackCount; stkI++) {
                if (line !== '') { line += ","; }
                line += this.data[stkI].name;
            }
        } else {
            // data
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

// Line -----------------------------------------------------------
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
