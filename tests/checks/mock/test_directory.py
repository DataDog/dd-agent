# stdlib
from itertools import product
import os
import shutil
import tempfile

# project
from tests.checks.common import AgentCheckTest


class DirectoryTestCase(AgentCheckTest):
    CHECK_NAME = 'directory'

    FILE_METRICS = [
        "system.disk.directory.file.bytes",
        "system.disk.directory.file.modified_sec_ago",
        "system.disk.directory.file.created_sec_ago"
    ]

    HISTOGRAM_SUFFIXES = ['count', '95percentile', 'max', 'median', 'avg']

    DIRECTORY_METRICS = [i1 + "." + i2 for i1, i2 in product([
        "system.disk.directory.file.bytes",
        "system.disk.directory.file.modified_sec_ago",
        "system.disk.directory.file.created_sec_ago"
    ], HISTOGRAM_SUFFIXES)]

    COMMON_METRICS = [
        "system.disk.directory.files",
        "system.disk.directory.bytes"
    ]

    @staticmethod
    def get_config_stubs(dir_name, filegauges=False):
        """
        Helper to generate configs from a directory name
        """
        return [
            {
                'directory': dir_name,
                'filegauges': filegauges
            }, {
                'directory': dir_name,
                'name': "my_beloved_directory",
                'filegauges': filegauges
            }, {
                'directory': dir_name,
                'dirtagname': "directory_custom_tagname",
                'filegauges': filegauges
            }, {
                'directory': dir_name,
                'filetagname': "file_custom_tagname",
                'filegauges': filegauges
            }, {
                'directory': dir_name,
                'dirtagname': "recursive_check",
                'recursive': True,
                'filegauges': filegauges
            }, {
                'directory': dir_name,
                'dirtagname': "pattern_check",
                'pattern': "*.log",
                'filegauges': filegauges
            }
        ]

    def setUp(self):
        """
        Generate a directory with a file structure for tests
        """
        self.temp_dir = tempfile.mkdtemp()

        # Create 10 files
        for i in xrange(0, 10):
            open(self.temp_dir + "/file_" + str(i), 'a').close()

        # Add 2 '.log' files
        open(self.temp_dir + "/log_1.log", 'a').close()
        open(self.temp_dir + "/log_2.log", 'a').close()

        # Create a subfolder and generate files into it
        os.makedirs(str(self.temp_dir) + "/subfolder")

        # Create 5 subfiles
        for i in xrange(0, 5):
            open(self.temp_dir + "/subfolder" + '/file_' + str(i), 'a').close()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_directory_metrics(self):
        """
        Directory metric coverage
        """
        config_stubs = self.get_config_stubs(self.temp_dir)

        config = {
            'instances': config_stubs
        }

        self.run_check(config)

        for config in config_stubs:
            dirtagname = config.get('dirtagname', "name")
            name = config.get('name', self.temp_dir)
            dir_tags = [dirtagname + ":%s" % name]

            # Directory metrics
            for mname in (self.DIRECTORY_METRICS + self.COMMON_METRICS):
                self.assertMetric(mname, tags=dir_tags, count=1)

            # 'recursive' and 'pattern' parameters
            if config.get('pattern'):
                # 2 '*.log' files in 'temp_dir'
                self.assertMetric("system.disk.directory.files", tags=dir_tags, count=1, value=2)
            elif config.get('recursive'):
                # 12 files in 'temp_dir' + 5 files in 'tempdir/subfolder'
                self.assertMetric("system.disk.directory.files", tags=dir_tags, count=1, value=17)
            else:
                # 12 files in 'temp_dir'
                self.assertMetric("system.disk.directory.files", tags=dir_tags, count=1, value=12)

        # Raises when COVERAGE=true and coverage < 100%
        self.coverage_report()

    def test_file_metrics(self):
        """
        File metric coverage
        """
        config_stubs = self.get_config_stubs(self.temp_dir, filegauges=True)

        config = {
            'instances': config_stubs
        }

        self.run_check(config)

        for config in config_stubs:
            dirtagname = config.get('dirtagname', "name")
            name = config.get('name', self.temp_dir)
            filetagname = config.get('filetagname', "filename")
            dir_tags = [dirtagname + ":%s" % name]

            # File metrics
            for mname in self.FILE_METRICS:
                # 2 '*.log' files in 'temp_dir'
                for i in xrange(1, 3):
                    file_tag = [filetagname + ":%s" % self.temp_dir + "/log_" + str(i) + ".log"]
                    self.assertMetric(mname, tags=dir_tags + file_tag, count=1)

                if not config.get('pattern'):
                    # Files in 'temp_dir'
                    for i in xrange(0, 10):
                        file_tag = [filetagname + ":%s" % self.temp_dir + "/file_" + str(i)]
                        self.assertMetric(mname, tags=dir_tags + file_tag, count=1)

                    # Files in 'temp_dir/subfolder'
                    if config.get('recursive'):
                        for i in xrange(0, 5):
                            file_tag = [filetagname + ":%s" % self.temp_dir + "/subfolder" + "/file_" + str(i)]
                            self.assertMetric(mname, tags=dir_tags + file_tag, count=1)

            # Common metrics
            for mname in self.COMMON_METRICS:
                self.assertMetric(mname, tags=dir_tags, count=1)

        # Raises when COVERAGE=true and coverage < 100%
        self.coverage_report()
