import logging
import subprocess
import tempfile
import unittest


class TestTail(unittest.TestCase):
    def setUp(self):
        self.log_file = tempfile.NamedTemporaryFile()
        self.logrotate_config = tempfile.NamedTemporaryFile()
        self.logrotate_config.write("""%s {
            copytruncate
            notifempty
            missingok
            rotate 1
            weekly
        }""" % self.log_file.name)
        self.logrotate_config.flush()
        self.logrotate_state_file = tempfile.NamedTemporaryFile()
    
    def _trigger_logrotate(self):
        subprocess.check_call([
            'logrotate', 
            '-v', # Verbose logging
            '-f', # Force the rotation even though the file isn't old
            # Create a state file that you have file permissions for
            '-s', self.logrotate_state_file.name, 
            self.logrotate_config.name
        ])    
    
    def test_logrotate_copytruncate(self):
        from checks.utils import TailFile
        
        line_parser = lambda line: line
        
        tail = TailFile(logging.getLogger(), self.log_file.name, line_parser)
        self.assertEquals(tail._size, 0)
        
        # Write some data to the log file
        init_string = "hey there, I am a log\n"
        self.log_file.write(init_string)
        self.log_file.flush()
        
        # Consume from the tail
        gen = tail.tail(line_by_line=False, move_end=True)
        gen.next()
        
        # Verify that the tail consumed the data I wrote
        self.assertEquals(tail._size, len(init_string))
        
        # Trigger a copytruncate logrotation on the log file
        self._trigger_logrotate()
        
        # Write a new line to the log file
        new_string = "I am shorter\n"
        self.log_file.write(new_string)
        self.log_file.flush()
        
        # Verify that the tail recognized the logrotation 
        self.assertEquals(tail._size, len(new_string))
        
        
        