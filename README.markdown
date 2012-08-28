The Datadog agent faithfully collects events and metrics and brings
them to [Datadog](https://app.datadoghq.com) on your behalf so that
you can do something with your monitoring and performance data.

You're looking at the source code right now. We provide a number of
[pre-packaged binaries](https://app.datadoghq.com/account/settings#agent] for your convenience.

# [Change log](https://github.com/DataDog/dd-agent/wiki/Change-Log)

# How to contribute code

Feel free to fork this repository and submit pull requests against the
`master` branch.

[![Build Status](https://secure.travis-ci.org/DataDog/dd-agent.png?branch=master)](http://travis-ci.org/DataDog/dd-agent)

# How to configure the agent

If you are using packages on linux, the configuration file lives in
`/etc/dd-agent/datadog.conf`. We provide and example in the same
directory that you can use as a template.

# How to instrument your own applications

## How to parse custom log files

The Datadog agent can read metrics directly from your log files, either

* from the Datadog canonical log format, without additional programming
* from any other log format, with a customized log parsing function

### Reading logs in the  Datadog canonical log format

Datadog logs are formatted as follows:

    metric unix_timestamp value [attribute1=v1 attributes2=v2 ...]

For example, imagining the content of  `/var/log/web.log` to be:

    me.web.requests 1320786966 157 metric_type=counter unit=request 
    me.web.latency 1320786966 250 metric_type=gauge unit=ms

Then all you need for Datadog to read metrics is to add this line to
your agent configuration file (usually at
`/etc/dd-agent/datadog.conf`):

    dogstreams: /var/log/web.log

You can also specify multiple log files like this:

    dogstreams: /var/log/web.log, /var/log/db.log, /var/log/cache.log

### Parsing custom log formats

If you don't have control over logging or can't issue your logs in the
canonical format, you may also tell the Datadog agent to use a custom
Python function to extract the proper fields from the log by adding
the following line to your agent configuration file:

    dogstreams: /var/log/web.log:parsers:parse_web

or
    dogstreams: /var/log/web.log:/home/dog/parsers.py:parse_web

The `parsers:parse_web` portion indicates that the custom Python
function lives in a package called `parsers` in the agent's
`PYTHONPATH`, and the parsers package has a function named
`parse_web`. The agent's `PYTHONPATH` is set in the agent startup
script, `/etc/init.d/datadog- agent` for agent versions < 2.0, and in
the supervisor config for agent version >= 2.0.

As an alternative you must use an absolute path to a parser python file
in case it does not reside in the `PYTHONPATH`.

`parsers.py` might look like this:

    import calendar
    from datetime import datetime

    def parse_web(logger, line, parser_state):
    	# parser_state is a dictionary into which you can stuff
        # stateful data that can be shared between invocation
        # of parse_web

        # Split the line into fields
        date, metric_name, metric_value, attrs = line.split('|')
        
        # Convert the iso8601 date into a unix timestamp
        date = datetime.strptime(date, "%Y-%m-%dT%H:%M:%S")
        date = calendar.timegm(date.timetuple())
        
        # Remove surrounding whitespace from the metric name
        metric_name = metric_name.strip()
        
        # Convert the metric value into a float
        metric_value = float(metric_value.strip())
        
        # Convert the attribute string field into a dictionary
        attr_dict = {}
        for attr_pair in attrs.split(','):
            attr_name, attr_val = attr_pair.split('=')
            attr_name = attr_name.strip()
            attr_val = attr_val.strip()
            attr_dict[attr_name] = attr_val
        
        # Return the output as a tuple
        return (metric_name, date, metric_value, attr_dict)

#### Custom parsing functions

* take two parameters: a Python `logger` object and a string parameter of the current line to parse. 
* return a tuple or list of tuples of the form:

`(metric (str), timestamp (unix timestamp), value (float), attributes (dict))`

Where attributes should at least contain the key `metric_type`,
specifying whether the given metric is a `counter` or `gauge`.

#### Stateful parsing functions

In some cases you will want to remember some data between each parsing function invocation.
The canonical example is counting the number of lines in a log.

    import calendar
    from datetime import datetime

    def count_lines(logger, line, parser_state):
    	# parser_state is a dictionary into which you can stuff
        # stateful data that can be shared between invocation
        # of parse_web

        # Split the line into fields
        date, metric_name, metric_value, attrs = line.split('|')
        
        # Convert the iso8601 date into a unix timestamp
        date = datetime.strptime(date, "%Y-%m-%dT%H:%M:%S")
        date = calendar.timegm(date.timetuple())
        
        # Remove surrounding whitespace from the metric name
        metric_name = metric_name.strip()
        
        # Count the number of lines and turn it into a metric
        acc = 0
        try:
            acc = parser_state["lines"] + 1
        except KeyError:
            parser_state["lines"] = 0

        parser_state["lines"] = acc
        
        # Return the output as a tuple
        return (metric_name, date, acc, {'metric_type': 'counter'})


#### Testing custom parsing functions

You'll want to be able to test your parser outside of the agent, so
for the above example, you might add a test function like this:

    def test():
        # Set up the test logger
        import logging 
        logging.basicConfig(level=logging.DEBUG)
        
        # Set up the test input and expected output
        test_input = "2011-11-08T21:16:06|me.web.requests|157|metric_type=counter,unit=request"
        expected = (
            "me.web.requests", 
            1320786966, 
            157, 
            {"metric_type": "counter", 
             "unit":        "request" }
        )
        
        # Call the parse function
        actual = parse_web(logging, test_input)
        
        # Validate the results
        assert expected == actual, "%s != %s" % (expected, actual)
        print 'test passes'
    
    
    if __name__ == '__main__':
        # For local testing, callable as "python /path/to/parsers.py"
        test()
        
And you can test your parsing logic by calling `python /path/to/parsers.py`.

## How to write custom checks

First you need to write a check that conforms to the `Check` interface defined in `checks/__init__.py`.
Then you need to enable that check via the agent configuration in `datadog.conf`.

An example of a custom check is provided in `examples/check_time.py`.