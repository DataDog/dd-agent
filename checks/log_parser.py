from checks import AgentCheck
from checks.utils import TailFile


class LogParserCheck(AgentCheck):

    def __init__(self, name, init_config, agentConfig):
        AgentCheck.__init__(self, name, init_config, agentConfig)

        self.parsers = {}

    def _instance_key(*args):
        """ Return a key unique for this instance """
        return '|'.join([str(a) for a in args])


class LogParser(object):

    def __init__(self, logger, log_path, move_end=False):
        self._line_parsed = 0
        self.log = logger
        self.log_path = log_path

        self.tail = TailFile(self.log, self.log_path, self._parse_line)
        self.gen = self.tail.tail(line_by_line=False, move_end=move_end)

        self.metric_data = []
        self.event_data = []

    def _parse_line(self, line):
        raise NotImplementedError()

    def parse_file(self):
        try:
            self.log.debug("Starting parse for file %s" % (self.log_path))
            self.tail._log = self.log
            self.gen.next()
            self.log.debug("Done parse for file %s (parsed %s line(s))" %
                (self.log_path, self._line_parsed))
        except StopIteration, e:
            self.log.warn("Can't tail %s file" % (self.log_path))
            raise

    def _get_metrics(self):
        metric_data = self.metric_data
        self.metric_data = []
        return metric_data

    def _get_events(self):
        event_data = self.event_data
        self.event_data = []
        return event_data
