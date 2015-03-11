# stdlib
from collections import defaultdict, deque
import copy
import inspect
import logging
import requests

# project
from config import _is_affirmative, format_proxy_settings, get_proxy, get_url_endpoint

log = logging.getLogger('governor')


class LimiterConfigError(Exception):
    """
    Error when parsing limiter
    """
    pass


class Governor(object):
    """
    Abstract Governor class
    """

    # Defines what's an 'active' context
    # i.e. number of iterations for which a context (not encountered anymore)
    # is kept stored before being flushed.
    _CONTEXTS_TTL = 3

    # Collector payload's metric format
    _METRIC_FORMAT = ['name', 'timestamp', 'value', 'attributes']

    # Governor report endpoint
    DATADOG_REPORT_GOVERNOR_URL = 'agent_governor/report'

    # Governor agent-specific static variables
    _CHECK_LIMITERS, _AGENT_LIMITERS = None, None
    _HOSTNAME = None
    _DD_URL = None
    _API_KEY = None

    @classmethod
    def init(cls, governor_config, agent_config, hostname):
        """
        Set Governor agent-specific variables
        """
        if not _is_affirmative(agent_config.get('use_governor', True)):
            return

        cls._CHECK_LIMITERS, cls._AGENT_LIMITERS = LimiterParser.parse_limiters(governor_config)
        cls._HOSTNAME = hostname
        cls._API_KEY = agent_config.get('api_key')

        # Set Governor report URL and proxy settings
        cls._GOVERNOR_URL = "{0}/{1}".format(
            get_url_endpoint(agent_config.get('dd_url', ""), endpoint_type='governor'),
            cls.DATADOG_REPORT_GOVERNOR_URL)
        cls._PROXY = format_proxy_settings(get_proxy(agent_config))

    @classmethod
    def get_agent_limiters(cls):
        return cls._AGENT_LIMITERS

    @classmethod
    def get_check_limiters(cls):
        return cls._CHECK_LIMITERS

    @classmethod
    def get_all_limiters(cls):
        return cls.get_agent_limiters() + cls.get_check_limiters()

    def __init__(self):
        self._iteration = 0

    def process(self, metrics, flush=False, report=False):
        """
        Asynchronous metric payload analysis
        """
        for m in metrics:
            named_args = self._name_args(m[0:3], m[3], asynchronous=True)
            self._check(named_args)

        statuses = self.get_status(flush=flush)

        # Report to Datadog when Governor limit is hit
        overflow_statuses = filter(lambda s: s['trace']['overflow_metrics'], statuses)
        if report and overflow_statuses:
            self._report_to_datadog(overflow_statuses)

        return statuses

    def _report_to_datadog(self, status):
        """
        Agent hit the active contexts limit set by the Governor.
        Send a warning email to Datadog team.
        """
        log.warning("Agent hit the active contexts limit set by the Governor."
                    "Sending a warning to Datadog team")

        try:
            # FIXME set actual data, once endpoint is ready
            data = ""
            log.debug("Performing post {0} to url {1}".format(data, self._GOVERNOR_URL))

            r = requests.post(self._GOVERNOR_URL, data=data, proxies=self._PROXY)
            r.raise_for_status()
        except (requests.ConnectionError, requests.exceptions.Timeout):
            log.exception("Unable to connect to url {0}".format(self._GOVERNOR_URL))
        except requests.exceptions.HTTPError as e:
            log.exception("HTTP error {0}. Something went wrong.".format(e.response.status_code))

    def get_status(self, flush=False):
        """
        Return limiter statuses and flush limiters
        """
        try:
            statuses = [l.get_status() for l in self._limiters]
        except TypeError:
            log.exception("Governor instantiated before being set.")
            return []

        # Flush limiters
        if flush:
            for l in self._limiters:
                l.flush(self._iteration - self._CONTEXTS_TTL)
            self._iteration += 1

        return statuses

    def _name_args(self, arg_list, kwargs, asynchronous=False):
        """
        Name `arg_list` items and merge with `kwargs`
        """
        named_args = kwargs.copy()
        for i, arg_value in enumerate(arg_list):
            if asynchronous:
                arg_name = self._METRIC_FORMAT[i]
            else:
                arg_name = self._submit_metric_arg_names[i + 1]
            named_args[arg_name] = arg_value
        return named_args

    def _check(self, args):
        """
        Check metric against all limiters
        """
        try:
            return all(r.check(self._iteration, args) for r in self._limiters)
        except TypeError:
            log.exception("Governor instantiated before being set.")
            return True


class CheckGovernor(Governor):
    """
    Monitor check's metric payload
    """
    def __init__(self):
        super(CheckGovernor, self).__init__()
        self._limiters = copy.deepcopy(self._CHECK_LIMITERS)

    def process(self, metrics):
        """
        Asynchronous check's metric payload analysis. Do not report on anomalies.
        """
        return super(CheckGovernor, self).process(metrics, flush=False, report=False)

    #####################################################
    # Governor as a decorator  for `real-time` analysis #
    #####################################################
    # Deprecated: will be removed once confirmed #
    ##############################################
    def set(self, func):
        """
        Set governor to run as a decorator
        """
        self._submit_metric = func
        self._submit_metric_arg_names = inspect.getargspec(func)[0]

    def __call__(self, *args, **kw):
        """
        Decorator purpose around `submit_metric` method for 'real-time' analysis
        """
        # Shortcut when no rules are defined
        if not self._limiters:
            return self._submit_metric(*args, **kw)

        # FIXME really dirty trick -> to improve
        named_args = self._name_args(args, kw)

        # Extract argument dict
        if self._check(named_args):
            return self._submit_metric(*args, **kw)


class AgentGovernor(Governor):
    """
    Monitor entire collector's metric payload
    """
    def __init__(self):
        super(AgentGovernor, self).__init__()
        self._limiters = copy.deepcopy(self._AGENT_LIMITERS)

    def process(self, metrics):
        """
        Asynchronous agent's metric payload analysis. Report on anomalies.
        """
        # FIXME keep `report` to False for now, until endpoint is ready
        return super(AgentGovernor, self).process(metrics, flush=True, report=False)


class LimiterParser(object):
    """
    Limiter parser
    """
    @staticmethod
    def parse_limiters(config):
        """
        Parse limiter config to limiters
        :param config: agent configuration
        :type config: dictionnary
        """
        limiters = [Limiter(r.get('scope'), r.get('selection'), r.get('limit'))
                    for r in config.get('limiters', [])]

        # Split limiters in two categories:
        # * Check limiters monitor check's metrics payload individually
        # * Agent limiters monitor the entire collector payload
        check_limiters = []
        agent_limiters = []

        for l in limiters:
            if 'check' in l._scope:
                check_limiters.append(l)
            else:
                agent_limiters.append(l)

        return check_limiters, agent_limiters


class Limiter(object):
    """
    A generic limiter
    """
    _ATOMS = frozenset(['name', 'agent', 'check', 'tags'])

    def __init__(self, scope, selection, limit=None):
        # Definition
        self._scope, self._selection = self._make_scope_and_selection(scope, selection)
        self._limit_cardinal = limit or "inf"

        # Metric values extractor
        self._extract_metric_keys = self._extract_to_keys(self._scope, self._selection)

        # Limiter data structure
        self._active_selections_by_scope = defaultdict(ExpiringSelection)

        # Trace
        self._overflow_metrics = 0

    @classmethod
    def _make_scope_and_selection(cls, scope, selection):
        """
        Check limiter `scope` and `selection` settings. Cast as a tuple and returns.

        :param scope: scope where the rule applies
        :type scope: string tuple or singleton

        :param selection: selection where the rule applies
        :type selection: string tuple or singleton
        """
        if not scope or not selection:
            raise LimiterConfigError("Limiters must contain a `scope` and a `selection`.")

        scope = scope if isinstance(scope, tuple) else (scope,)
        selection = selection if isinstance(selection, tuple) else (selection,)

        for s in scope:
            if s not in cls._ATOMS:
                raise LimiterConfigError("Unrecognized `{0}` within `scope`. `scope` must"
                                         " be a subset of {1}".format(s, cls._ATOMS))
        for s in selection:
            if s not in cls._ATOMS:
                raise LimiterConfigError("Unrecognized `{0}` within `selection`. `selection` must"
                                         " be a subset of {1}".format(s, cls._ATOMS))

        return scope, selection

    @classmethod
    def _extract_to_keys(cls, scope, selection):
        """
        Return a function that extracts scope and selection values from a metric

        :param scope: scope where the rule applies
        :type scope: string tuple or singleton

        :param selection: selection where the rule applies
        :type selection: string tuple or singleton
        """
        def get(d, k):
            """
            Return hashable d.get(k)
            """
            v = d.get(k)
            if isinstance(v, list):
                v = tuple(v)
            return v

        return lambda x: (tuple(get(x, k) for k in scope), tuple(get(x, k) for k in selection))

    def check(self, ts, metric):
        """
        Limiter main task.
        Check incoming metrics against the limit set, and returns a boolean

        :param ts: metric timestamp (i.e. governor iteration)
        :param metric: metric named parameters
        """
        scope_value, selection_value = self._extract_metric_keys(metric)

        active_scope_selections = self._active_selections_by_scope[scope_value]

        if selection_value in active_scope_selections:
            active_scope_selections.add(selection_value, 1)
            return True
        else:
            if len(active_scope_selections) >= self._limit_cardinal:
                self._overflow_metrics += 1
                log.warning("Metric overflow {0}. {1} hit the {2} limit set."
                            .format(self._overflow_metrics, metric, self._limit_cardinal))
                return False
            active_scope_selections.add(selection_value, ts)
            return True

    def flush(self, max_timestamp):
        """
        Flush every scope's active selections
        :param max_timestamp: cut off timestamp
        """
        for _, active_selections in self._active_selections_by_scope.iteritems():
            active_selections.flush(max_timestamp)
        self._overflow_metrics = 0

    def get_status(self):
        """
        Return limiter trace:
        `scope_cardinal`            -> Number of scopes registred
        `overflow_metrics`          -> Number of overflow metrics
        `scope_overflow_cardinal`   -> Number of scope with selection overflows
        `max_selection_scope`       -> Scope with the maximum of selections registred
        `max_selection_cardinal`    -> Maximum number of selections registred for a scope
        """
        scope_cardinal = len(self._active_selections_by_scope)
        scope_overflow_cardinal = 0
        max_selection_scope = None
        max_selection_cardinal = 0

        for scope, selections in self._active_selections_by_scope.iteritems():
            if max_selection_cardinal < len(selections):
                max_selection_cardinal = len(selections)
                max_selection_scope = scope
            if len(selections) >= self._limit_cardinal:
                scope_overflow_cardinal += 1

        return {
            'definition': {
                'scope': self._scope,
                'selection': self._selection,
                'limit': self._limit_cardinal
            },
            'trace': {
                'scope_cardinal': scope_cardinal,
                'overflow_metrics': self._overflow_metrics,
                'scope_overflow_cardinal': scope_overflow_cardinal,
                'max_selection_scope': max_selection_scope,
                'max_selection_cardinal': max_selection_cardinal
            }
        }


class ExpiringSelection(object):
    """
    Active selections storage
    """
    def __init__(self):
        self._timestamp_by_selection = {}   # Active selections
        self._selection_queue = deque()     # Selection timestamps window

    def __len__(self):
        """
        Return unique not-expired selections cardinal
        """
        return len(self._timestamp_by_selection)

    def __contains__(self, selection):
        return selection in self._timestamp_by_selection

    def add(self, selection, timestamp):
        """
        Add selection
        """
        self._timestamp_by_selection[selection] = timestamp
        self._selection_queue.append((timestamp, selection))

    def flush(self, max_timestamp):
        """
        Remove expired selections
        """
        while self._selection_queue and self._selection_queue[0][0] <= max_timestamp:
            expiry, key = self._selection_queue.popleft()
            if self._timestamp_by_selection.get(key) == expiry:
                del self._timestamp_by_selection[key]
