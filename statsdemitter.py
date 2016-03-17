import statsd

from checks.metric_types import MetricTypes


def emitter(message, log, agentConfig, endpoint):
    "Send payload"
    log.debug('statsd_emitter: attempting postback to {host}:{port}'.format(host=agentConfig['statsd_host'], port=agentConfig['statsd_port']))
    c = statsd.StatsClient(agentConfig['statsd_host'], agentConfig['statsd_port'], agentConfig['statsd_prefix'], agentConfig['statsd_maxudpsize'])

    value_by_name, type_by_name = _aggregate_metrics(message['metrics'])
    for name, value in value_by_name.iteritems():
        if type_by_name[name] == MetricTypes.GAUGE:
            c.gauge(name, value)
        if type_by_name[name] == MetricTypes.COUNTER:
            c.incr(name, value)
        if type_by_name[name] == MetricTypes.RATE:
            c.gauge(name, value) # Not real statsd equivalent
        if type_by_name[name] == MetricTypes.COUNT:
            c.gauge(name, value) # Not real statsd equivalent

def _aggregate_metrics(metrics):
    "To deal with metric with the same name and different tags we just average them"
    value_by_name = {}
    type_by_name = {}

    for metric in metrics:
        name = metric[0]
        # We are going to assume to assume 2 metrics with the same name share the same type
        type_by_name[name] = metric[3]['type']
        value_by_name.setdefault(name, [])
        value_by_name[name].append(metric[2])

    for name in value_by_name:
        value_by_name[name] = list_average(value_by_name[name])
    return value_by_name, type_by_name

def list_average(list):
    sum = 0
    for item in list:
        sum += item
    return sum/len(list)
