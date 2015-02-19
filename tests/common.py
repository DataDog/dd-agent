# stdlib
import inspect
import os
from pprint import pprint
import signal
import sys
import unittest

# project
from checks import AgentCheck
from config import get_checksd_path
from util import get_os, get_hostname

def get_check_class(name):
    checksd_path = get_checksd_path(get_os())
    if checksd_path not in sys.path:
        sys.path.append(checksd_path)

    check_module = __import__(name)
    check_class = None
    classes = inspect.getmembers(check_module, inspect.isclass)
    for _, clsmember in classes:
        if clsmember == AgentCheck:
            continue
        if issubclass(clsmember, AgentCheck):
            check_class = clsmember
            if AgentCheck in clsmember.__bases__:
                continue
            else:
                break

    return check_class

def load_check(name, config, agentConfig):
    checksd_path = get_checksd_path(get_os())
    if checksd_path not in sys.path:
        sys.path.append(checksd_path)

    check_module = __import__(name)
    check_class = None
    classes = inspect.getmembers(check_module, inspect.isclass)
    for _, clsmember in classes:
        if clsmember == AgentCheck:
            continue
        if issubclass(clsmember, AgentCheck):
            check_class = clsmember
            if AgentCheck in clsmember.__bases__:
                continue
            else:
                break
    if check_class is None:
        raise Exception("Unable to import check %s. Missing a class that inherits AgentCheck" % name)

    init_config = config.get('init_config', {})
    instances = config.get('instances')
    agentConfig['checksd_hostname'] = get_hostname(agentConfig)

    # init the check class
    try:
        return check_class(name, init_config=init_config, agentConfig=agentConfig, instances=instances)
    except Exception as e:
        raise Exception("Check is using old API, {0}".format(e))

def kill_subprocess(process_obj):
    try:
        process_obj.terminate()
    except AttributeError:
        # py < 2.6 doesn't support process.terminate()
        if get_os() == 'windows':
            import ctypes
            PROCESS_TERMINATE = 1
            handle = ctypes.windll.kernel32.OpenProcess(PROCESS_TERMINATE, False,
                process_obj.pid)
            ctypes.windll.kernel32.TerminateProcess(handle, -1)
            ctypes.windll.kernel32.CloseHandle(handle)
        else:
            os.kill(process_obj.pid, signal.SIGKILL)

def get_check(name, config_str):
    checksd_path = get_checksd_path(get_os())
    if checksd_path not in sys.path:
        sys.path.append(checksd_path)
    check_module = __import__(name)
    check_class = None
    classes = inspect.getmembers(check_module, inspect.isclass)
    for name, clsmember in classes:
        if AgentCheck in clsmember.__bases__:
            check_class = clsmember
            break
    if check_class is None:
        raise Exception("Unable to import check %s. Missing a class that inherits AgentCheck" % name)

    agentConfig = {
        'version': '0.1',
        'api_key': 'tota'
    }

    return check_class.from_yaml(yaml_text=config_str, check_name=name,
        agentConfig=agentConfig)

def read_data_from_file(filename):
    return open(os.path.join(os.path.dirname(__file__), 'data', filename)).read()


class AgentCheckTest(unittest.TestCase):
    DEFAULT_AGENT_CONFIG = {
        'version': '0.1',
        'api_key': 'toto'
    }

    def __init__(self, *args, **kwargs):
        super(AgentCheckTest, self).__init__(*args, **kwargs)

        if not hasattr(self, 'CHECK_NAME'):
            raise Exception("You must define CHECK_NAME")

        self.check = None

    def run_check(self, config, agent_config=None):
        agent_config = agent_config or self.DEFAULT_AGENT_CONFIG

        # If not loaded already, do it!
        if self.check is None:
            self.check = load_check(self.CHECK_NAME, config, agent_config)

        error = None
        for instance in self.check.instances:
            try:
                self.check.check(instance)
            except Exception, e:
                # Catch error before re-raising it to be able to get service_checks
                print"Exception {0} during check"
                error = e

        self.metrics = self.check.get_metrics()
        self.events = self.check.get_events()
        self.service_checks = self.check.get_service_checks()
        self.warnings = self.check.get_warnings()

        if error is not None:
            raise error

    def print_current_state(self):
        print "++++++++++++ DEBUG ++++++++++++"
        print "METRICS ",
        pprint(self.metrics)
        print "---------"
        print "EVENTS",
        pprint(self.events)
        print "---------"
        print "SERVICE CHECKS",
        pprint(self.service_checks)
        print "---------"
        print "WARNINGS",
        pprint(self.warnings)
        print "---------"
        print "++++++++++++ DEBUG ++++++++++++"

    def _candidates_size_assert(self, candidates, count=None, tolerance=1):
        try:
            if count is not None:
                self.assertEquals(len(candidates), count,
                    "Needed exactly %d candidates, got %d" % (count, len(candidates))
                )
            else:
                self.assertTrue(len(candidates) >= tolerance,
                    "Needed at least %d candidates, got %d" % (tolerance, len(candidates))
                )
        except AssertionError:
            self.print_current_state()
            raise


    def assertMetric(self, metric_name, metric_value=None, tags=None, count=None):
        candidates = []
        for m_name, ts, val, mdata in self.metrics:
            if m_name == metric_name:
                if metric_value is not None and val != metric_value:
                    continue
                if tags is not None and sorted(tags) != sorted(mdata.get("tags", [])):
                    continue

                candidates.append((m_name, ts, val, mdata))

        self._candidates_size_assert(candidates, count=count)


    def assertMetricTagPrefix(self, metric_name, tag_prefix, count=None):
        candidates = []
        for m_name, ts, val, mdata in self.metrics:
            if m_name == metric_name:
                gtags = [t for t in mdata['tags'] if t.startswith(tag_prefix)]
                if not gtags:
                    continue
                candidates.append((m_name, ts, val, mdata))

        self._candidates_size_assert(candidates, count=count)

    def assertMetricTag(self, metric_name, tag, count=None):
        candidates = []
        for m_name, ts, val, mdata in self.metrics:
            if m_name == metric_name:
                gtags = [t for t in mdata['tags'] if t == tag]
                if not gtags:
                    continue
                candidates.append((m_name, ts, val, mdata))

        self._candidates_size_assert(candidates, count=count)

    def assertServiceCheck(self, service_check_name, status=None, tags=None, count=None):
        candidates = []
        for sc in self.service_checks:
            if sc['check'] == service_check_name:
                if status is not None and sc['status'] != status:
                    continue
                if tags is not None and sorted(tags) != sorted(sc.get("tags")):
                    continue

                candidates.append(sc)

        self._candidates_size_assert(candidates, count=count)
