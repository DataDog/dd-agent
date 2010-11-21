import telnetlib
import traceback

class Ganglia(object):

    def check(self, logger, agentConfig):
        logger.debug('get ganglia status: start')

        logger.debug("Config: %s" % agentConfig)
        if 'ganglia_host' not in agentConfig or agentConfig['ganglia_host'] == '':
            logger.debug('ganglia_host configuration not set, not checking ganglia')
            return False

        host = agentConfig['ganglia_host']
        port = 8651

        if 'ganglia_port' in agentConfig and agentConfig['ganglia_port'] != '':
            port = int(agentConfig['ganglia_port'])

        logger.debug("Using port %d" % port)

        try:
            tn = telnetlib.Telnet(host,port)
            data = tn.read_all()

        except Exception,e:
            logger.error("Unable to get ganglia data, Exception:" + traceback.format_exc())
            return False

        logger.debug('get ganglia status: done')
        return data
