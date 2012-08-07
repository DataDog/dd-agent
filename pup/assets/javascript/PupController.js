/* PupController.js
 * Coordinates UI for pup
 *
 * Public interface:
 *  tryStart()      : starts controller if not already created
 *  isRunning()     : accessor returns whether or not the controller is running
 *  n()             : accessor returns number of datapoints
 */

var PupController = function(isWSClosed, Store, $) {
    var minutes     = 10,                                   // window period
        duration    = Math.sqrt(minutes * 60 * 1000),       // transitions work best if duration and n are close in value
                                                            //  duration represents the buffer time window for transitions
        n           = Math.ceil(duration),                  // number of data points
        step        = 0,                                    // if smooth transitions are enabled, this signifies the lag
        now         = new Date(Date.now() - duration),      // now set to current time minus a transition period
        running     = false,                                // determines whether PupController is running
        metrics     = [],                                   // an array of all the Metric objects
        graphsByName= {},                                   // an object of all the graph objects, keyed by metric name
        sideByName  = {},                                   // an object of all the entries objects, keyed by metric name
        format      = d3.format(".2s");                     // defines format. rounding to two significant digits.

    // private helpers --------------------------------------------------

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
                metric  : metric,
                element : container,
                n       : n,
                duration: duration,
                now     : +now
            });
        } else if (metric.type !== "histogram") {
            graphsByName[metric.name] = new LineGraph({
                metric  : metric,
                element : container,
                n       : n,
                duration: duration,
                now     : +now
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
        $('#waiting').addClass("hidden");
        $('#data-streaming').addClass("hidden");
        $('#disconnected').removeClass("hidden");
        $('#listening').html("Not " + $('#listening').html());
        window.scrollTo(0,0);
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

            var i = metrics.length;
            while (i--) {
                var metric = metrics[i];

                // set metric's timedOut value and time
                metric.setIfTimedOut(now);

                if (!graphsByName.hasOwnProperty(metric.name)) {
                    var creationTime = new Date();
                    addEntry(metric, creationTime);
                    addGraph(metric, creationTime);
                }

                graph = graphsByName[metric.name];
                graph.updateScales(now);
                
                // push most recent data point on
                if (metric.hasNewData()) {
                    metric.pushRecent();
                } else if (metric.timedOut.is) {
                    metric.pushNull(new Date());
                }

                // check if progress bar needs to be drawn
                graph.tryDrawProgress(now);
                
                // redraw the area/line
                graph.redraw(now);

                // shift off the old
                var timeWindow = +now - (minutes * 60000 + metric.freq);
                metric.shiftOld(timeWindow);

                // update entry
                graph.updateLatestVal(now);

                // update sidebar
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

    // public interface --------------------------------------------------
    var pub = {};

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

        // interact public interface -----------------------------------------
        var intPub = {};

        // internally updates plot counts   
        intPub.updatePlotCount = function() {
            var graphDivs   = document.getElementById('graphs').children,
                shownCount  = 0;

            $(graphDivs).each(function() {
                if ( $(this).is(':visible') ) {
                    shownCount++;
                }
            });
            
            graphCount      = shownCount;
            totalGraphCount = graphDivs.length;
        };

        // filter graphs and their corresponding sidebar entries by term
        intPub.filterBy = function(term) {
            var graphDivs   = document.getElementById('graphs').children,
                entryLis    = document.getElementById('metric-list').children,
                lowerTerm   = term.toLowerCase(),
                i           = graphDivs.length;

            while (i--) {
                var id      = graphDivs[i].id,
                    lowerId = id.toLowerCase(),
                    re      = new RegExp(lowerTerm, 'gi');
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

        // sorting interface
        intPub.sort = function() {
            var graphsRoot          = document.getElementById('graphs'),
                graphsRootChildren  = graphsRoot.children,
                entriesRoot         = document.getElementById('metric-list'),
                entriesRootChildren = entriesRoot.children,
                graphsArray         = [],
                entriesArray        = [],
                i                   = graphsRootChildren.length;

            // private sorting helpers -------------------------------------
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

            // sort public interface ---------------------------------------    
            var sortPub = {};

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
                var active = $(".sort-active")[0].getAttribute(C.ID);
                if (active === "by-name") {
                    sortPub.byName();
                } else { sortPub.byTimeAdded(); }
            };

            return sortPub;
        };
        
        // filter shown metrics by active tags
        intPub.filterByTags = function(t) {
            var graphDivs       = document.getElementById('graphs').children,
                entries         = document.getElementById('metric-list').children,
                tags            = document.getElementById('tag-list').children,
                i               = graphDivs.length,
                tagSelected     = t[0],
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
                for (var j = 0, len = tags.length; j < len; j++) {
                    if ($(tags[j]).hasClass("tag-active")) {
                        activeTags[activeTags.length] = tags[j].getAttribute("tag");
                    }
                }

                // for each plot
                while (i--) {
                    key = graphDivs[i].getAttribute(C.NAME);
                    var graphTags = Store.getMetricByName(key).tags,
                        k = activeTags.length;

                    // if no tags are selected, show all
                    if (!activeTags.length) {
                        graphDivs[i].style.display = "";
                        entries[i].style.display = "";
                    } else {
                        // else, check if current graph's tags match active tags
                        while (k--) {
                            if (graphTags.indexOf(activeTags[k]) > -1) { break; }
                        }
                
                        // if current graph's tags match active tags, show them
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

                // add highlighted graph tags
                $(".graph-tag").each(function() {
                    if ($(this).html() === $(tagSelected).html()) {
                        $(this).css("color", "#6f56a2");
                    }
                });

                while (i--) {
                    key = graphDivs[i].getAttribute(C.NAME);

                    // hide those plots that don't match the tag just selected
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

        // highlights graph
        intPub.highlightGraph = function(metricName) {
            var graph = $(".plot-box[name=\"" + metricName + '\"]');
            var graphHeader = $(graph).find('h5');
            $(graphHeader).addClass("highlight-graph-header");
            $(graph).addClass("highlight-graph");
            var entry = $('li[name=\"' + metricName + '\"]');
            $(entry).addClass("highlight-metric");
            return intPub;
        };

        // scroll to the graph just clicked on in the entries list
        intPub.scrollToGraph = function(metricName) {
            var graph = $('.plot-box[name=\"' + metricName + '\"]');
            var y = $(graph).offset().top;
            window.scrollTo(0, y - 15);
            return intPub;
        };

        // fade the graph when the mouse leaves the entry
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

    // accessor for the number of datapoints in each graph
    pub.n = function() { return n; };

    return pub;
}(PupSocket.isClosed, Store, $);
