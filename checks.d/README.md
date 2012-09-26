# Writing Custom Checks

## Configuration

Each check will have a configuration file that will be placed in the `conf.d`
directory. Configuration is written using [YAML](http://www.yaml.org/). The
file name should match the name of the check module (e.g.: `haproxy.py` and `haproxy.yaml`).

The configuration file has the following structure:

```yaml
init_config:
    key1: val1
    key2: val2

instances:
    - username: jon_smith
      password: 1234

    - username: jane_smith
      password: 5678
```

### `init_config`

The `init_config` section allows you to have an arbitrary number of global configuration
options that will be available on every run of the check in `self.config`.

### `instances`

The `instances` section is a list of instances that this check will be run against.
Your actual `check()` method is run once per instance. This means that every check
will support multiple instances out of the box.

## Check Module

All checks inherit from the `AgentCheck` class found in `checks/__init__.py` and
require a `check()` method that takes one argument, `instance` which is a `dict`
having the configuration of an instance.

### Sending metrics

Sendings metrics in a custom check is easy! If you're already familiar with the
methods available in DogstatsD, then the transition will be very simple. If not,
you'll find that the submitting metrics is a breeze.

You have the following methods available to you:

```python
self.gauge( ... ) # Sample a gauge metric

self.increment( ... ) # Increment a counter metric

self.decrement( ... ) # Decrement a counter metric

self.histogram( ... ) # Sample a histogram metric

self.rate( ... ) # Sample a point, with the rate calcualted at the end of the check

```

All of these methods take the following arguments:

- `metric`: The name of the metric
- `value`: The value for the metric (defaults to 1 on increment, -1 on decrement)
- `tags`: (optional) A list of tags to associate with this metric.
- `hostname`: (optional) A hostname to associate with this metric. Defaults to the current host.
- `device_name`: (optional) A device name to associate with this metric.

These methods may be called from anywhere within your check logic. At the end of
your `check` function, all metrics that were submitted will be collected and flushed
out with the other agent metrics.

### Sending events

Sending an event from a custom check is simple! At any time during your check,
you can make a call to `self.event(...)` with one argument: the payload of the event.
Your event should be structured like this:

```python
{
    "timestamp": int, the epoch timestamp for the event,
    "event_type": string, the event time name,
    "api_key": string, the api key of the account to associate the event with,
    "msg_title": string, the title of the event,
    "msg_text": string, the text body of the event,
    "aggregation_key": string, a key to aggregate events on,
    "alert_type": (optional) string, one of ('error', 'warning', 'success', 'info').
        Defaults to 'info'.
    "source_type_name": (optional) string, the source type name,
    "host": (optional) string, the name of the host,
    "tags": (optional) list, a list of tags to associate with this event
}
```

At the end of your check, all events will be collected and flushed with the rest
of the agent payload.

### Logging

As part of the parent class, you're given a logger at `self.log`, so you can do
things like `self.log.info('hello')`. The log handler will be `checks.{name}`
where `{name}` is the name of your check (taken from the filename of the check
module).

## A Sample Check

We've written a quick sample check to show this stuff in action.

The check will check the response time for a list of URLs defined in configuration
and will submit an event if (a) the event times out or (b) the response code is
something other than 200 (OK).

In `checks.d/http.py`:

```python
import time
import requests

from checks import AgentCheck
from hashlib import md5

class HTTPCheck(AgentCheck):
    def check(self, instance):
        if 'url' not in instance:
            self.log.info("Skipping instance, no url found.")
            return

        # Load values from the instance config
        url = instance['url']
        timeout = float(instance.get('timeout', 5))

        # Use a hash of the URL as an aggregation key
        aggregation_key = md5(url).hexdigest()

        # Check the URL
        start_time = time.time()
        try:
            r = requests.get(url, timeout=timeout)
            end_time = time.time()
        except requests.exceptions.Timeout as e:
            # If there's a timeout
            self.timeout_event(url, timeout, aggregation_key)
            return

        if r.status_code != 200:
            self.status_code_event(url, r, aggregation_key)
            return

        timing = end_time - start_time
        self.gauge('http.reponse_time', timing, tags=[url])

    def timeout_event(self, url, timeout, aggregation_key):
        self.event({
            'timestamp': int(time.time()),
            'event_type': 'http_check',
            'msg_title': 'URL timeout',
            'msg_text': '%s timed out after %s seconds.' % (url, timeout),
            'aggregation_key': aggregation_key
        })

    def status_code_event(self, url, r, aggregation_key):
        self.event({
            'timestamp': int(time.time()),
            'event_type': 'http_check',
            'msg_title': 'Invalid reponse code for %s' % url,
            'msg_text': '%s returned a status of %s' % (url, r.status_code),
            'aggregation_key': aggregation_key
        })
```

In `conf.d/http.yaml`:

```yaml
init_config:

instances:
    -   url: https://google.com

    -   url: http://httpbin.org/delay/10
        timeout: 8

    -   url: http://httpbin.org/status/400
```
