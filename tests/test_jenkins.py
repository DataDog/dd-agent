import unittest
import os
from collections import defaultdict
import datetime
import tempfile
import shutil
import logging

from tests.common import get_check

logger = logging.getLogger(__file__)

DATETIME_FORMAT = '%Y-%m-%d_%H-%M-%S'
LOG_DATA = 'Finished: SUCCESS'

BUILD_METADATA = """
    <build>
      <number>20783</number>
      <result>SUCCESS</result>
      <duration>487</duration>
    </build>
"""
NO_RESULT_YET_METADATA = """
    <build>
      <number>20783</number>
      <duration>487</duration>
    </build>
"""

CONFIG = """
init_config:

instances:
    -   name: default
        jenkins_home: <JENKINS_HOME>
"""

class TestJenkins(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.config_yaml = CONFIG.replace('<JENKINS_HOME>', self.tmp_dir)

    def tearDown(self):
        # Clean up the temp directory
        shutil.rmtree(self.tmp_dir)

    def _create_builds(self, metadata):
        # As coded, the jenkins dd agent needs more than one result
        # in order to get the last valid build.
        today = datetime.date.today()
        yesterday = today - datetime.timedelta(days=1)

        old_date = yesterday.strftime(DATETIME_FORMAT)
        todays_date = today.strftime(DATETIME_FORMAT)

        self._create_build(old_date, metadata)
        self._create_build(todays_date, metadata)

    def _create_check(self):
        # Create the jenkins check
        self.check, instances = get_check('jenkins', self.config_yaml)
        self.instance = instances[0]

    def _create_build(self, datestring, metadata):
        # The jenkins dd agent requires the build metadata file and a log file of results
        build_dir = os.path.join(self.tmp_dir, 'jobs', 'foo', 'builds', datestring)
        os.makedirs(build_dir)

        metadata_file = open(os.path.join(build_dir, 'build.xml'), 'w+b')
        log_file = open(os.path.join(build_dir, 'log'), 'w+b')

        log_data = LOG_DATA
        self._write_file(log_file, log_data)

        build_metadata = metadata
        self._write_file(metadata_file, build_metadata)

    def _write_file(self, log_file, log_data):
        log_file.write(log_data)
        log_file.flush()

    def testParseBuildLog(self):
        """
        Test doing a jenkins check. This will parse the logs but since there was no
        previous high watermark no event will be created.
        """
        self._create_builds(BUILD_METADATA)
        self._create_check()
        self.check.check(self.instance)

        # The check method does not return anything, so this testcase passes
        #  if the high_watermark was set and no exceptions were raised.
        self.assertTrue(self.check.high_watermarks[self.instance['name']]['foo'] > 0)

    def testCheckCreatesEvents(self):
        """
        Test that a successful build will create metrics to report in.
        """
        self._create_builds(BUILD_METADATA)
        self._create_check()

        # Set the high_water mark so that the next check will create events
        self.check.high_watermarks['default'] = defaultdict(lambda: 0)

        # Do a check
        self.check.check(self.instance)

        results = self.check.get_metrics()
        metrics = [r[0] for r in results]

        assert 'jenkins.job.success' in metrics
        assert 'jenkins.job.duration' in metrics
        assert len(metrics) == 2

    def testCheckWithRunningBuild(self):
        """
        Test under the conditions of a jenkins build still running.
        The build.xml file will exist but it will not yet have a result.
        """
        self._create_builds(NO_RESULT_YET_METADATA)
        self._create_check()

        # Set the high_water mark so that the next check will create events
        self.check.high_watermarks['default'] = defaultdict(lambda: 0)

        self.check.check(self.instance)

        # The check method does not return anything, so this testcase passes
        # if the high_watermark was NOT updated and no exceptions were raised.
        assert self.check.high_watermarks[self.instance['name']]['foo'] == 0

if __name__ == '__main__':
    unittest.main()
