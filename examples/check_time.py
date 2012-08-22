from checks import Check
import time

class SecondCheck(Check):
    """An example of a custom check.
    
    To use it you need to place this file in a directory that is reachable by the dd-agent user
    and let the agent know of its location via the following stanza in /etc/dd-agent/datadog.conf
    
    custom_checks: /my/director/check_time.py:SecondCheck
    """

    def __init__(self, logger):
        """Declare a single gauge that will record the second value of its invocation"""
        # Super-initialization
        Check.__init__(self, logger)
        self.logger.info("Initializing custom check %s" % self.__class__)
        # Declare which metric(s) you want to save
        self.gauge("dd.custom.agent.second")
        self.counter("dd.custom.agent.check_rate")

    def check(self, agentConfig):
        """You must implement the check method, with one argument, agentConfig"""
        self.logger.info("Custom check %s called" % self.__class__)
        self.save_sample("dd.custom.agent.second", int(time.time()) % 10)
        self.save_sample("dd.custom.agent.check_rate", int(time.time()))
        return self.get_metrics()
