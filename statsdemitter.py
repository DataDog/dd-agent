import statsd

def emitter(message, log, agentConfig, endpoint):
    "Send payload"
    log.debug('statsd_emitter: attempting postback to {host}:{port}'.format(host=agentConfig['statsd_host'], port=agentConfig['statsd_port']))
    statsd.StatsClient(agentConfig['statsd_host'], agentConfig['statsd_port'], agentConfig['statsd_prefix'], agentConfig['statsd_maxudpsize'])
