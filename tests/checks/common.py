# stdlib
import copy
import inspect
import logging
import os
from pprint import pformat
import signal
import sys
import time
import traceback
import unittest

# project
from checks import AgentCheck
from config import get_checksd_path
from util import get_hostname, get_os
from utils.debug import get_check  # noqa -  FIXME 5.5.0 AgentCheck tests should not use this

log = logging.getLogger('tests')


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


class Fixtures(object):
    @staticmethod
    def integration_name():
        for stack in inspect.stack():
            # stack[1] is the file path
            file_name = os.path.basename(stack[1])
            if 'test_' in file_name:
                # test_name.py
                #      5   -3
                return file_name[5:-3]
        raise Exception('No integration test file in stack')

    @staticmethod
    def directory():
        return os.path.join(os.path.dirname(__file__), 'fixtures',
                            Fixtures.integration_name())

    @staticmethod
    def file(file_name):
        return os.path.join(Fixtures.directory(), file_name)

    @staticmethod
    def read_file(file_name):
        return open(Fixtures.file(file_name)).read()


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

    def is_travis(self):
        return "TRAVIS" in os.environ

    def load_check(self, config, agent_config=None):
        agent_config = agent_config or self.DEFAULT_AGENT_CONFIG
        self.check = load_check(self.CHECK_NAME, config, agent_config)

    # Helper function when testing rates
    def run_check_twice(self, config, agent_config=None, mocks=None,
                        force_reload=False):
        self.run_check(config, agent_config, mocks, force_reload)
        time.sleep(1)
        self.run_check(config, agent_config, mocks)

    def run_check(self, config, agent_config=None, mocks=None, force_reload=False):
        # If not loaded already, do it!
        if self.check is None or force_reload:
            self.load_check(config, agent_config=agent_config)
        if mocks is not None:
            for func_name, mock in mocks.iteritems():
                if not hasattr(self.check, func_name):
                    continue
                else:
                    setattr(self.check, func_name, mock)

        error = None
        for instance in self.check.instances:
            try:
                # Deepcopy needed to avoid weird duplicate tagging situations
                # ie the check edits the tags of the instance, problematic if
                # run twice
                self.check.check(copy.deepcopy(instance))
                # FIXME: This should be called within the `run` method only
                self.check._roll_up_instance_metadata()
            except Exception, e:
                # Catch error before re-raising it to be able to get service_checks
                print "Exception {0} during check".format(e)
                print traceback.format_exc()
                error = e
        self.metrics = self.check.get_metrics()
        self.events = self.check.get_events()
        self.service_checks = self.check.get_service_checks()
        self.service_metadata = self.check.get_service_metadata()
        self.warnings = self.check.get_warnings()

        # pylint doesn't understand that we are raising this only if it's here
        if error is not None:
            raise error  # pylint: disable=E0702

    def print_current_state(self):
        log.debug("""++++++++ CURRENT STATE ++++++++
METRICS
    {metrics}

EVENTS
    {events}

SERVICE CHECKS
    {sc}

SERVICE METADATA
    {sm}

WARNINGS
    {warnings}
++++++++++++++++++++++++++++""".format(
            metrics=pformat(self.metrics),
            events=pformat(self.events),
            sc=pformat(self.service_checks),
            sm=pformat(self.service_metadata),
            warnings=pformat(self.warnings)
        ))

    def coverage_report(self):
        total_metrics = len(self.metrics)
        tested_metrics = 0
        untested_metrics = []
        for m in self.metrics:
            if m[3].get('tested'):
                tested_metrics += 1
            else:
                untested_metrics.append(m)
        if total_metrics == 0:
            coverage_metrics = 100.0
        else:
            coverage_metrics = 100.0 * tested_metrics / total_metrics

        total_sc = len(self.service_checks)
        tested_sc = 0
        untested_sc = []
        for sc in self.service_checks:
            if sc.get('tested'):
                tested_sc += 1
            else:
                untested_sc.append(sc)

        if total_sc == 0:
            coverage_sc = 100.0
        else:
            coverage_sc = 100.0 * tested_sc / total_sc

        total_sm = len(self.service_metadata)
        tested_sm = 0
        untested_sm = []
        for sm in self.service_metadata:
            if sm.get('tested'):
                tested_sm += 1
            else:
                untested_sm.append(sm)

        if total_sm == 0:
            coverage_sm = 100.0
        else:
            coverage_sm = 100.0 * tested_sm / total_sm

        coverage = """Coverage
========================================
    METRICS
        Tested {tested_metrics}/{total_metrics} ({coverage_metrics}%)
        UNTESTED: {untested_metrics}

    SERVICE CHECKS
        Tested {tested_sc}/{total_sc} ({coverage_sc}%)
        UNTESTED: {untested_sc}

    SERVICE METADATA
        Tested {tested_sm}/{total_sm} ({coverage_sm}%)
        UNTESTED: {untested_sm}
========================================"""
        log.info(coverage.format(
            tested_metrics=tested_metrics,
            total_metrics=total_metrics,
            coverage_metrics=coverage_metrics,
            untested_metrics=pformat(untested_metrics),
            tested_sc=tested_sc,
            total_sc=total_sc,
            coverage_sc=coverage_sc,
            untested_sc=pformat(untested_sc),
            tested_sm=tested_sm,
            total_sm=total_sm,
            coverage_sm=coverage_sm,
            untested_sm=pformat(untested_sm),
        ))

        if os.getenv('COVERAGE'):
            self.assertEquals(coverage_metrics, 100.0)
            self.assertEquals(coverage_sc, 100.0)
            self.assertEquals(coverage_sm, 100.0)

    def _candidates_size_assert(self, candidates, count=None, at_least=1):
        try:
            if count is not None:
                self.assertEquals(
                    len(candidates), count,
                    "Needed exactly %d candidates, got %d" % (count, len(candidates))
                )
            else:
                self.assertTrue(
                    len(candidates) >= at_least,
                    "Needed at least %d candidates, got %d" % (at_least, len(candidates))
                )
        except AssertionError:
            self.print_current_state()
            raise

    def assertMetric(self, metric_name, value=None, tags=None, count=None,
                     at_least=1, hostname=None, device_name=None):
        candidates = []
        for m_name, ts, val, mdata in self.metrics:
            if m_name == metric_name:
                if value is not None and val != value:
                    continue
                if tags is not None and sorted(tags) != sorted(mdata.get("tags", [])):
                    continue
                if hostname is not None and mdata['hostname'] != hostname:
                    continue
                if device_name is not None and mdata['device_name'] != device_name:
                    continue

                candidates.append((m_name, ts, val, mdata))

        try:
            self._candidates_size_assert(candidates, count=count, at_least=at_least)
        except AssertionError:
            log.error("Candidates size assertion for {0} (value: {1}, tags: {2}, "
                      "count: {3}, at_least: {4}, hostname: {5}) failed"
                      .format(metric_name, value, tags, count, at_least, hostname))
            raise

        for mtuple in self.metrics:
            for cmtuple in candidates:
                if mtuple == cmtuple:
                    mtuple[3]['tested'] = True
        log.debug("{0} FOUND !".format(metric_name))

    def assertMetricTagPrefix(self, metric_name, tag_prefix, count=None, at_least=1):
        log.debug("Looking for a tag starting with `{0}:` on metric {1}"
                  .format(tag_prefix, metric_name))
        if count is not None:
            log.debug(" * should have exactly {0} data points".format(count))
        elif at_least is not None:
            log.debug(" * should have at least {0} data points".format(at_least))

        candidates = []
        for m_name, ts, val, mdata in self.metrics:
            if m_name == metric_name:
                gtags = [t for t in mdata['tags'] if t.startswith(tag_prefix)]
                if not gtags:
                    continue
                candidates.append((m_name, ts, val, mdata))

        try:
            self._candidates_size_assert(candidates, count=count)
        except AssertionError:
            log.error("Candidates size assertion for {0} (tag_prefix: {1}, "
                      "count: {2}, at_least: {3}) failed".format(metric_name,
                                                                 tag_prefix,
                                                                 count,
                                                                 at_least))
            raise

        for mtuple in self.metrics:
            for cmtuple in candidates:
                if mtuple == cmtuple:
                    mtuple[3]['tested'] = True
        log.debug("{0} FOUND !".format(metric_name))

    def assertMetricTag(self, metric_name, tag, count=None, at_least=1):
        log.debug("Looking for tag {0} on metric {1}".format(tag, metric_name))
        if count is not None:
            log.debug(" * should have exactly {0} data points".format(count))
        elif at_least is not None:
            log.debug(" * should have at least {0} data points".format(at_least))

        candidates = []
        for m_name, ts, val, mdata in self.metrics:
            if m_name == metric_name:
                gtags = [t for t in mdata['tags'] if t == tag]
                if not gtags:
                    continue
                candidates.append((m_name, ts, val, mdata))

        try:
            self._candidates_size_assert(candidates, count=count)
        except AssertionError:
            log.error("Candidates size assertion for {0} (tag: {1}, count={2},"
                      " at_least={3}) failed".format(metric_name, tag, count, at_least))
            raise

        for mtuple in self.metrics:
            for cmtuple in candidates:
                if mtuple == cmtuple:
                    mtuple[3]['tested'] = True
        log.debug("{0} FOUND !".format(metric_name))

    def assertServiceMetadata(self, meta_keys, count=None, at_least=1):
        log.debug("Looking for service metadata with keys {0}".format(meta_keys))
        if count is not None:
            log.debug(" * should be defined for exactly {0} instances".format(count))
        elif at_least is not None:
            log.debug(" * should be defined for at least {0} instances".format(at_least))

        candidates = []
        for sm in self.service_metadata:
            if sorted(sm.keys()) != sorted(meta_keys):
                continue

            candidates.append(sm)

        try:
            self._candidates_size_assert(candidates, count=count, at_least=at_least)
        except AssertionError:
            log.error("Candidates size assertion for service metadata with keys {0}"
                      " (count: {1}, at_least: {2}) failed".format(meta_keys, count, at_least))
            raise

        for sm in self.service_metadata:
            for csm in candidates:
                if sm == csm:
                    sm['tested'] = True
        log.debug("Service metadata FOUND !")

    def assertServiceCheck(self, service_check_name, status=None, tags=None,
                           count=None, at_least=1):
        log.debug("Looking for service check {0}".format(service_check_name))
        if status is not None:
            log.debug(" * with status {0}".format(status))
        if tags is not None:
            log.debug(" * tagged with {0}".format(tags))
        if count is not None:
            log.debug(" * should have exactly {0} statuses".format(count))
        elif at_least is not None:
            log.debug(" * should have at least {0} statuses".format(at_least))
        candidates = []
        for sc in self.service_checks:
            if sc['check'] == service_check_name:
                if status is not None and sc['status'] != status:
                    continue
                if tags is not None and sorted(tags) != sorted(sc.get("tags")):
                    continue

                candidates.append(sc)

        try:
            self._candidates_size_assert(candidates, count=count, at_least=at_least)
        except AssertionError:
            log.error("Candidates size assertion for {0} (status: {1}, "
                      "tags: {2}, count: {3}, at_least: {4}) failed".format(service_check_name,
                                                                            status,
                                                                            tags,
                                                                            count,
                                                                            at_least))
            raise

        for sc in self.service_checks:
            for csc in candidates:
                if sc == csc:
                    sc['tested'] = True
        log.debug("{0} FOUND !".format(service_check_name))

    def assertServiceCheckOK(self, service_check_name, tags=None, count=None, at_least=1):
        self.assertServiceCheck(service_check_name,
                                status=AgentCheck.OK,
                                tags=tags,
                                count=count,
                                at_least=at_least)

    def assertServiceCheckWarning(self, service_check_name, tags=None, count=None, at_least=1):
        self.assertServiceCheck(service_check_name,
                                status=AgentCheck.WARNING,
                                tags=tags,
                                count=count,
                                at_least=at_least)

    def assertServiceCheckCritical(self, service_check_name, tags=None, count=None, at_least=1):
        self.assertServiceCheck(service_check_name,
                                status=AgentCheck.CRITICAL,
                                tags=tags,
                                count=count,
                                at_least=at_least)

    def assertServiceCheckUnknown(self, service_check_name, tags=None, count=None, at_least=1):
        self.assertServiceCheck(service_check_name,
                                status=AgentCheck.UNKNOWN,
                                tags=tags,
                                count=count,
                                at_least=at_least)

    def assertIn(self, first, second):
        self.assertTrue(first in second, "{0} not in {1}".format(first, second))

    def assertNotIn(self, first, second):
        self.assertTrue(first not in second, "{0} in {1}".format(first, second))

    def assertWarning(self, warning, count=None, at_least=1, exact_match=True):
        log.debug("Looking for warning {0}".format(warning))
        if count is not None:
            log.debug(" * should have exactly {0} statuses".format(count))
        elif at_least is not None:
            log.debug(" * should have at least {0} statuses".format(count))

        if exact_match:
            candidates = [w for w in self.warnings if w == warning]
        else:
            candidates = [w for w in self.warnings if warning in w]

        try:
            self._candidates_size_assert(candidates, count=count, at_least=at_least)
        except AssertionError:
            log.error("Candidates size assertion for {0}, count: {1}, "
                "at_least: {2}) failed".format(warning, count, at_least))
            raise

        log.debug("{0} FOUND !".format(warning))
