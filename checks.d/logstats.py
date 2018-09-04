# (C) Chris Moultrie <chris@moultrie.org> 2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)


# stdlib
import os
import time

# project
from checks import AgentCheck


class LogStats(AgentCheck):
    """This check is for calculating stats on log lines containing key terms

    WARNING: the user/group that dd-agent runs as must have access to stat the log specified

    Config options:
        "logfile" - string, the directory to gather stats for. required
        "ignores" - list, ignore a log line if it contains this keyword
    """

    SOURCE_TYPE_NAME = 'system'

    def _get_marker_filename(self, filename):
        """Gets the filename which holds our last known position in the logfile"""
        return os.path.join('/', 'tmp', "%s.ddmark" % (os.path.basename(filename),))

    def _get_marker_pos(self, filename):
        """Gets the last used position in the log file
        Returns -1 if we don't have a marker
        """
        marker_path = self._get_marker_filename(filename)
        marker_pos = -1

        if os.path.exists(marker_path):
            with open(marker_path, 'r') as marker_file:
                marker_pos = marker_file.read()
                marker_pos = int(marker_pos)

        if marker_pos == -1:
            self.log.info("No marker file found, setting marker to end of file.")

        return marker_pos

    def _set_marker_pos(self, filename, position):
        """Sets the position that we finished parsing the log file at"""
        marker_path = self._get_marker_filename(filename)
        self.log.debug("Writing marker for file: %s @ %d", filename, position)
        with open(marker_path, 'w+') as marker_file:
            marker_file.write(str(position))

    def _submit_event(self, filename, line, alert_type):
        event = {
            "timestamp": int(time.time()),
            "event_type": "logstats",
            "msg_title": "ERROR in %s" % (filename,),
            "msg_text": line,
            "alert_type": alert_type,
            "source_type_name": "my apps",
            "tags": ["filename:%s" % (os.path.basename(filename),)],
        }
        self.event(event)

    def _count_items(self, filename, position, ignores):
        """Count how many ERRORS and WARNINGS we see in the logs
        filename is the name of the file to parse
        position is where we should start parsing from
        """
        errors = 0
        warnings = 0

        with open(filename) as logfile:
            # Find out how long the file is, we need to know if it rotated
            logfile.seek(0, os.SEEK_END)
            end = logfile.tell()
            self.log.debug("End of log file is: %d, last position is %d", end, position)

            # If our previous marker is greater than the possible positions in the file, it's
            # rotated, we need to start over
            if end < position:
                self.log.debug("End of log file is: %d, last position is %d", end, position)
                position = 0

            # If we never had a position before, go to the end of the file, we'll start from there
            # otherwise, we can start at the last place we ended
            if position == -1:
                logfile.seek(position, os.SEEK_END)
            else:
                logfile.seek(position, os.SEEK_SET)

            # Iterate through the rest of the file, looking for ERROR or WARNING
            for line in logfile:
                skip_line = False
                for ignore in ignores:
                    if ignore in line:
                        skip_line = True
                        break
                if skip_line:
                    continue

                if "ERROR" in line:
                    errors += 1
                    self._submit_event(filename, line, 'error')
                elif "WARNING" in line:
                    warnings += 1

            # Update the marker file with our new end
            self._set_marker_pos(filename, logfile.tell())
        self.log.debug("Found %d errors and %d warnings in file %s", errors, warnings, filename)

        return errors, warnings

    def check(self, instance):
        """This is the method we override from AgentCheck
        It is called during the check and does the reporting
        """
        logfilename = instance.get('logfile')
        ignores = instance.get('ignores', [])
        if logfilename is None:
            self.log.info('Skipping instance, No log file specified')
            return

        marker_pos = self._get_marker_pos(logfilename)
        errors, warnings = self._count_items(logfilename, marker_pos, ignores)
        self.increment('logstats.errors.count', errors, ["filename:%s" %
                                                         (os.path.basename(logfilename))])
        self.increment('logstats.warnings.count', warnings, ["filename:%s" %
                                                             (os.path.basename(logfilename))])


if __name__ == '__main__':
    check, instances = LogStats.from_yaml('/etc/dd-agent/conf.d/logstats.yaml')
    for instance in instances:
        print "\nRunning the check against logfile: %s" % (instance['logfile'])
        check.check(instance)
        if check.has_events():
            print 'Events: %s' % (check.get_events())
        print 'Metrics: %s' % (check.get_metrics())
