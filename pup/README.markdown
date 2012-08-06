# Pup

Pup faithfully collects and displays metrics at localhost from Statsd. It's a hassle-free, open-source developer tool that comes bundled with the Datadog agent, meant to tighten the feedback loop on development.

### Installation

First install the [Datadog agent](https://github.com/DataDog/dd-agent) by running in the command prompt

    $ sh -c "$(curl -L http://dtdg.co/setup-pup)"

That's it! Now navigate to **localhost:17125**. Within ten seconds, system metrics should start streaming.

### Upgrade

It's easy, just re-install. No files will be lost.

### Custom metrics with statsd

If you would like to add custom metrics to your applications, use the dogstatsd-python or dogstatsd-ruby libraries to instrument your code. Thorough documentation on using DogStatsd and Statsd can be found at [Datadog HQ](http://api.datadoghq.com/guides/dogstatsd/). Below is an abridged introduction to Statsd, and an walkthrough on getting custom metrics viewed on Pup.

__Important__:

- DogStatsd aggregates many data points for a single metric over a certain time period (ten seconds by default).
- The "." separator in a metric name creates metric stacks. The separator indicates to Pup that it should group metrics under the namespace defined by what's left of the first "." in the metric name. For example, Pup will visually group both "users.cache.miss", and "users.cache.hit" under a single metric called "users"; it will group "signup.male" and "signup.female" under a single metric called "signup".

##### Python

If you haven't already, install the Python library

    $ sudo easy_install dogstatsd-python

Import the library and include it in the code of your choice

    # An example to count database queries
    from statsd import statsd

    def query_my_database():
      statsd.increment("database query count", tags=['db'])
      # Run the query…

Execute this code, and voilá! Metrics should be appearing any second now at localhost:17125.

##### Ruby

If you haven't already, install the dogstatsd-ruby gem

    $ gem install dogstatsd-ruby

Require the gem and initialize a new instance of Statsd in the code or your choice

    # An example to time page rendering
    require 'statsd'
    require 'sinatra'

    statsd = Statsd.new()

    get '/' do
      statsd.time('page render time', :tags => ['users']) do
        erb :index
      end
    end

Navigate to localhost:17125. Whoa! Insight.

-----------------------------------
Made with love by the Datadog team. Contributions are more than welcome!

Questions? Email [support@datadoghq.com](support@datadoghq.com).
