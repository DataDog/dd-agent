# (C) Datadog, Inc. 2013-2016
# (C) Brett Langdon <brett@blangdon.com> 2013
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)


# stdlib
from fnmatch import fnmatch
from os import stat
from os.path import abspath, exists, join
import time

# 3p
from scandir import walk

# project
from checks import AgentCheck
from config import _is_affirmative


class DirectoryCheck(AgentCheck):
    """This check is for monitoring and reporting metrics on the files for a provided directory

    WARNING: the user/group that dd-agent runs as must have access to stat the files in the desired directory

    Config options:
        "directory" - string, the directory to gather stats for. required
        "name" - string, the name to use when tagging the metrics. defaults to the "directory"
        "dirtagname" - string, the name of the tag used for the directory. defaults to "name"
        "tagsubdirs" - string, when true subdirs will be tagged on appropreiate metrics when recursing. default False
        "subdirtagname" - string, the name of the tag used for the subdirectory. defaults to "subdir"
        "filetagname" - string, the name of the tag used for each file. defaults to "filename"
        "filegauges" - boolean, when true stats will be an individual gauge per file (max. 20 files!) and not a histogram of the whole directory. default False
        "subdirgauges" - boolean, when true a total stat will be emitted for each subdirectory. default False
        "histograms" - boolean, when true histograms for filesizes and times will be generated. default True
        "pattern" - string, the `fnmatch` pattern to use when reading the "directory"'s files. default "*"
        "recursive" - boolean, when true the stats will recurse into directories. default False
        "countonly" - boolean, when true the stats will only count the number of files matching the pattern. Useful for very large directories.
    """

    SOURCE_TYPE_NAME = 'system'

    def check(self, instance):
        if "directory" not in instance:
            raise Exception('DirectoryCheck: missing "directory" in config')

        directory = instance["directory"]
        abs_directory = abspath(directory)
        name = instance.get("name", directory)
        pattern = instance.get("pattern", "*")
        recursive = _is_affirmative(instance.get("recursive", False))
        dirtagname = instance.get("dirtagname", "name")
        tagsubdirs = _is_affirmative(instance.get("tagsubdirs", False))
        subdirtagname = instance.get("subdirtagname", "subdir")
        filetagname = instance.get("filetagname", "filename")
        filegauges = _is_affirmative(instance.get("filegauges", False))
        subdirgauges = _is_affirmative(instance.get("subdirgauges", False))
        histograms = _is_affirmative(instance.get("histograms", True))
        countonly = _is_affirmative(instance.get("countonly", False))

        if not exists(abs_directory):
            raise Exception("DirectoryCheck: the directory (%s) does not exist" % abs_directory)

        self._get_stats(abs_directory, name, dirtagname, tagsubdirs, subdirtagname, filetagname, filegauges, subdirgauges, histograms, pattern, recursive, countonly)

    def _get_stats(self, directory, name, dirtagname, tagsubdirs, subdirtagname, filetagname, filegauges, subdirgauges, histograms, pattern, recursive, countonly):
        orig_dirtags = [dirtagname + ":%s" % name]
        directory_bytes = 0
        directory_files = 0
        recurse_count = 0
        for root, dirs, files in walk(directory):
            subdir_bytes = 0
            if recursive and tagsubdirs and recurse_count > 0:
                dirtags = [subdirtagname + ":%s" % root, "is_subdir:true"] + list(orig_dirtags)
            else:
                dirtags = ["is_subdir:true"] + list(orig_dirtags)

            for filename in files:
                filename = join(root, filename)
                # check if it passes our filter
                if not fnmatch(filename, pattern):
                    continue

                directory_files += 1

                # We're just looking to count the files, don't stat it as well
                if countonly:
                    continue

                try:
                    file_stat = stat(filename)

                except OSError as ose:
                    self.warning("DirectoryCheck: could not stat file %s - %s" % (filename, ose))
                else:
                    # file specific metrics
                    subdir_bytes += file_stat.st_size
                    directory_bytes += subdir_bytes
                    if filegauges and directory_files <= 20:
                        filetags = list(dirtags)
                        filetags.append((filetagname + ":%s" % filename).encode('ascii', 'ignore'))
                        self.gauge("system.disk.directory.file.bytes", file_stat.st_size, tags=filetags)
                        self.gauge("system.disk.directory.file.modified_sec_ago", time.time() - file_stat.st_mtime, tags=filetags)
                        self.gauge("system.disk.directory.file.created_sec_ago", time.time() - file_stat.st_ctime, tags=filetags)
                    elif not filegauges and histograms:
                        self.histogram("system.disk.directory.file.bytes", file_stat.st_size, tags=dirtags)
                        self.histogram("system.disk.directory.file.modified_sec_ago", time.time() - file_stat.st_mtime, tags=dirtags)
                        self.histogram("system.disk.directory.file.created_sec_ago", time.time() - file_stat.st_ctime, tags=dirtags)

            if recurse_count > 0 and subdirgauges and not countonly:
                # If we've descended in to a subdir then let's emit total for the subdir
                self.gauge("system.disk.directory.bytes", subdir_bytes, tags=dirtags)

            # os.walk gives us all sub-directories and their files
            # if we do not want to do this recursively and just want
            # the top level directory we gave it, then break
            recurse_count += 1
            if not recursive:
                break

        # number of files
        self.gauge("system.disk.directory.files", directory_files, tags=orig_dirtags)
        # total file size
        if not countonly:
            self.gauge("system.disk.directory.bytes", directory_bytes, tags=orig_dirtags)
