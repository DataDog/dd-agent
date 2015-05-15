# stdlib
from collections import defaultdict
import datetime
import logging
import os
import shutil
import tempfile
import unittest

# 3p
import xml.etree.ElementTree as ET

# project
from tests.checks.common import get_check

logger = logging.getLogger(__file__)

DATETIME_FORMAT = '%Y-%m-%d_%H-%M-%S'
LOG_DATA = 'Finished: SUCCESS'

SUCCESSFUL_BUILD = {'number': '99', 'result': 'SUCCESS', 'duration': '60'}
NO_RESULTS_YET = {'number': '99', 'duration': '60'}
UNSUCCESSFUL_BUILD = {'number': '99', 'result': 'ABORTED', 'duration': '60'}

CONFIG = """
init_config:

instances:
    -   name: default
        jenkins_home: <JENKINS_HOME>
"""


def dict_to_xml(metadata_dict):
    """ Convert a dict to xml for use in a build.xml file """
    build = ET.Element('build')
    for k, v in metadata_dict.iteritems():
        node = ET.SubElement(build, k)
        node.text = v

    return ET.tostring(build)


def write_file(file_name, log_data):
    with open(file_name, 'w') as log_file:
        log_file.write(log_data)


class TestJenkins(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.config_yaml = CONFIG.replace('<JENKINS_HOME>', self.tmp_dir)
        self._create_old_build()

    def tearDown(self):
        # Clean up the temp directory
        shutil.rmtree(self.tmp_dir)

    def _create_old_build(self):
        # As coded, the jenkins dd agent needs more than one result
        # in order to get the last valid build.
        # Create one for yesterday.
        metadata = dict_to_xml(SUCCESSFUL_BUILD)
        yesterday = datetime.date.today() - datetime.timedelta(days=1)
        self._populate_build_dir(metadata, yesterday)

    def _create_check(self):
        # Create the jenkins check
        self.check, instances = get_check('jenkins', self.config_yaml)
        self.instance = instances[0]

    def _populate_build_dir(self, metadata, time=None):
        # The jenkins dd agent requires the build metadata file and a log file of results
        time = time or datetime.datetime.now()
        datestring = time.strftime(DATETIME_FORMAT)
        build_dir = os.path.join(self.tmp_dir, 'jobs', 'foo', 'builds', datestring)
        os.makedirs(build_dir)

        log_file = os.path.join(build_dir, 'log')
        log_data = LOG_DATA
        write_file(log_file, log_data)

        metadata_file = os.path.join(build_dir, 'build.xml')
        build_metadata = metadata
        write_file(metadata_file, build_metadata)

    def testParseBuildLog(self):
        """
        Test doing a jenkins check. This will parse the logs but since there was no
        previous high watermark no event will be created.
        """
        metadata = dict_to_xml(SUCCESSFUL_BUILD)

        self._populate_build_dir(metadata)
        self._create_check()
        self.check.check(self.instance)

        # The check method does not return anything, so this testcase passes
        #  if the high_watermark was set and no exceptions were raised.
        self.assertTrue(self.check.high_watermarks[self.instance['name']]['foo'] > 0)

    def testCheckSuccessfulEvent(self):
        """
        Test that a successful build will create the correct metrics.
        """
        metadata = dict_to_xml(SUCCESSFUL_BUILD)

        self._populate_build_dir(metadata)
        self._create_check()

        # Set the high_water mark so that the next check will create events
        self.check.high_watermarks['default'] = defaultdict(lambda: 0)

        self.check.check(self.instance)

        metrics = self.check.get_metrics()

        metrics_names = [m[0] for m in metrics]
        assert len(metrics_names) == 2
        assert 'jenkins.job.success' in metrics_names
        assert 'jenkins.job.duration' in metrics_names

        metrics_tags = [m[3] for m in metrics]
        for tag in metrics_tags:
            assert 'job_name:foo' in tag.get('tags')
            assert 'result:SUCCESS' in tag.get('tags')
            assert 'build_number:99' in tag.get('tags')

    def testCheckUnsuccessfulEvent(self):
        """
        Test that an unsuccessful build will create the correct metrics.
        """
        metadata = dict_to_xml(UNSUCCESSFUL_BUILD)

        self._populate_build_dir(metadata)
        self._create_check()

        # Set the high_water mark so that the next check will create events
        self.check.high_watermarks['default'] = defaultdict(lambda: 0)

        self.check.check(self.instance)

        metrics = self.check.get_metrics()

        metrics_names = [m[0] for m in metrics]
        assert len(metrics_names) == 2
        assert 'jenkins.job.failure' in metrics_names
        assert 'jenkins.job.duration' in metrics_names

        metrics_tags = [m[3] for m in metrics]
        for tag in metrics_tags:
            assert 'job_name:foo' in tag.get('tags')
            assert 'result:ABORTED' in tag.get('tags')
            assert 'build_number:99' in tag.get('tags')

    def testCheckWithRunningBuild(self):
        """
        Test under the conditions of a jenkins build still running.
        The build.xml file will exist but it will not yet have a result.
        """
        metadata = dict_to_xml(NO_RESULTS_YET)

        self._populate_build_dir(metadata)
        self._create_check()

        # Set the high_water mark so that the next check will create events
        self.check.high_watermarks['default'] = defaultdict(lambda: 0)

        self.check.check(self.instance)

        # The check method does not return anything, so this testcase passes
        # if the high_watermark was NOT updated and no exceptions were raised.
        assert self.check.high_watermarks[self.instance['name']]['foo'] == 0
